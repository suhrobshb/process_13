"""
RAG (Retrieval-Augmented Generation) Engine
===========================================

This module provides the core functionality for the RAG engine, which is responsible
for processing user-specific data sources and enabling context-aware AI decision-making.

Key Features:
- Integrates with LangChain for robust document loading, splitting, and vectorization.
- Supports various data sources like local directories (text, PDF) and web pages.
- Uses FAISS for efficient local vector storage and retrieval.
- Provides a query interface to retrieve context and generate answers from an LLM.
- Designed with multi-tenancy in mind, storing data segregated by user.
"""

import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

# LangChain components
from langchain.vectorstores import FAISS
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.document_loaders import (
    PyPDFLoader,
    TextLoader,
    WebBaseLoader,
    DirectoryLoader,
)
from langchain.chains.question_answering import load_qa_chain
from langchain.llms import OpenAI
from langchain.prompts import PromptTemplate

# Database/Models
from sqlmodel import Session, SQLModel, Field, create_engine, select
from .database import get_session

# --- Configuration ---
# Logging setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("rag_engine")

# Check for OpenAI API Key
if not os.getenv("OPENAI_API_KEY"):
    logger.warning("OPENAI_API_KEY environment variable not set. RAG engine may not function correctly.")

# --- Data Models ---
class RAGDataSource(SQLModel, table=True):
    """Represents a data source for the RAG engine."""
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    source_type: str  # e.g., 'directory', 'web', 'pdf_directory'
    uri: str  # e.g., file path, URL
    user_id: int = Field(foreign_key="user.id")
    tenant_id: int = Field(foreign_key="tenant.id")
    status: str = Field(default="pending")  # pending, processing, completed, failed
    last_processed: Optional[datetime] = None
    vector_store_path: Optional[str] = None

# --- RAG Engine ---
class RAGEngine:
    """
    Handles document ingestion, vectorization, and retrieval for RAG workflows.
    """
    def __init__(self, user_id: int, tenant_id: int):
        self.user_id = user_id
        self.tenant_id = tenant_id
        self.vector_store_dir = Path(f"storage/users/{self.user_id}/rag_stores")
        self.vector_store_dir.mkdir(parents=True, exist_ok=True)
        self.embeddings = OpenAIEmbeddings()

    def _get_loader(self, source_type: str, uri: str):
        """Returns the appropriate LangChain document loader."""
        if source_type == "directory":
            # Simple loader for text files in a directory
            return DirectoryLoader(uri, glob="**/*.txt", loader_cls=TextLoader, recursive=True)
        elif source_type == "pdf_directory":
            return DirectoryLoader(uri, glob="**/*.pdf", loader_cls=PyPDFLoader, recursive=True)
        elif source_type == "web":
            return WebBaseLoader(uri)
        # Add more loaders as needed (e.g., for databases, other file types)
        else:
            raise ValueError(f"Unsupported data source type: {source_type}")

    def process_data_source(self, data_source: RAGDataSource):
        """Loads, splits, and vectorizes documents from a data source."""
        logger.info(f"Processing data source {data_source.id}: {data_source.name}")
        data_source.status = "processing"
        self._update_data_source_status(data_source)

        try:
            # 1. Load documents
            logger.info(f"Loading documents from {data_source.uri}")
            loader = self._get_loader(data_source.source_type, data_source.uri)
            documents = loader.load()
            if not documents:
                logger.warning(f"No documents found for data source {data_source.id}")
                data_source.status = "completed"
                self._update_data_source_status(data_source)
                return

            # 2. Split documents into chunks
            logger.info(f"Splitting {len(documents)} documents into chunks")
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
            texts = text_splitter.split_documents(documents)

            # 3. Create and save vector store
            logger.info(f"Creating vector store from {len(texts)} text chunks")
            vector_store = FAISS.from_documents(texts, self.embeddings)
            
            # Save the vector store locally
            store_path = str(self.vector_store_dir / f"store_{data_source.id}")
            vector_store.save_local(store_path)
            
            # Update data source record
            data_source.status = "completed"
            data_source.vector_store_path = store_path
            data_source.last_processed = datetime.utcnow()
            self._update_data_source_status(data_source)
            
            logger.info(f"Successfully processed data source {data_source.id}")

        except Exception as e:
            logger.error(f"Failed to process data source {data_source.id}: {e}", exc_info=True)
            data_source.status = "failed"
            self._update_data_source_status(data_source)

    def _update_data_source_status(self, data_source: RAGDataSource):
        """Updates the status of a data source in the database."""
        with get_session() as session:
            session.add(data_source)
            session.commit()
            session.refresh(data_source)

    def _load_vector_store(self, data_source_id: int) -> Optional[FAISS]:
        """Loads a specific vector store from local storage."""
        store_path = self.vector_store_dir / f"store_{data_source_id}"
        if store_path.exists():
            logger.info(f"Loading vector store from {store_path}")
            return FAISS.load_local(str(store_path), self.embeddings, allow_dangerous_deserialization=True)
        logger.warning(f"Vector store not found for data source {data_source_id}")
        return None

    def query(self, query_text: str, data_source_ids: List[int]) -> Dict[str, Any]:
        """
        Queries the RAG system with a given text against specified data sources.
        """
        if not data_source_ids:
            return {"answer": "No data sources specified for the query.", "source_documents": []}

        # For this implementation, we'll query the first available vector store.
        # A more advanced implementation would merge results from multiple stores.
        vector_store = self._load_vector_store(data_source_ids[0])
        if not vector_store:
            return {"answer": f"Could not load data source {data_source_ids[0]}.", "source_documents": []}

        logger.info(f"Querying with text: '{query_text}'")
        
        # Define a prompt template
        prompt_template = """Use the following pieces of context to answer the question at the end. If you don't know the answer, just say that you don't know, don't try to make up an answer.

        {context}

        Question: {question}
        Helpful Answer:"""
        PROMPT = PromptTemplate(template=prompt_template, input_variables=["context", "question"])

        # Create a question-answering chain
        chain = load_qa_chain(OpenAI(temperature=0), chain_type="stuff", prompt=PROMPT)
        
        # Retrieve relevant documents
        docs = vector_store.similarity_search(query_text, k=4)
        
        # Run the chain
        result = chain({"input_documents": docs, "question": query_text}, return_only_outputs=True)

        return {
            "answer": result.get("output_text", "No answer found."),
            "source_documents": [doc.metadata for doc in docs]
        }

# --- API Integration Example (for context, not implementation here) ---
# In a separate routers/rag_router.py file, you would have:
#
# from fastapi import APIRouter, Depends, BackgroundTasks
# from ..auth import get_current_user
# from ..models.user import User
# from .rag_engine import RAGEngine, RAGDataSource
#
# router = APIRouter(prefix="/rag", tags=["rag"])
#
# @router.post("/data_sources")
# def add_source(source: RAGDataSource, background_tasks: BackgroundTasks, user: User = Depends(get_current_user)):
#     # Save source to DB
#     # ...
#     engine = RAGEngine(user.id, user.tenant_id)
#     background_tasks.add_task(engine.process_data_source, source)
#     return {"message": "Data source processing started."}
#
# @router.post("/query")
# def query_rag(query: str, source_ids: List[int], user: User = Depends(get_current_user)):
#     engine = RAGEngine(user.id, user.tenant_id)
#     return engine.query(query, source_ids)
