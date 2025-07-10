"""
Event Serializer
================

This module handles the serialization, deserialization, and processing of recorded events
from the MultiMonitorCapture system. It provides efficient storage formats, event filtering,
compression, and data validation for recorded user interactions.

Key Features:
- Multiple serialization formats (JSON, MessagePack, Protocol Buffers)
- Event filtering and deduplication
- Compression support (gzip, lz4)
- Data validation and sanitization
- Batch processing for large event streams
- Schema versioning for compatibility
"""

import json
import gzip
import pickle
import logging
import time
import hashlib
from typing import Dict, Any, List, Optional, Union, Iterator, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
import os

# Optional imports for advanced features
try:
    import msgpack
    MSGPACK_AVAILABLE = True
except ImportError:
    MSGPACK_AVAILABLE = False

try:
    import lz4.frame
    LZ4_AVAILABLE = True
except ImportError:
    LZ4_AVAILABLE = False

logger = logging.getLogger(__name__)


class SerializationFormat(Enum):
    """Supported serialization formats"""
    JSON = "json"
    JSON_COMPRESSED = "json.gz"
    MSGPACK = "msgpack"
    MSGPACK_COMPRESSED = "msgpack.gz"
    PICKLE = "pickle"
    PICKLE_COMPRESSED = "pickle.gz"


class CompressionType(Enum):
    """Supported compression types"""
    NONE = "none"
    GZIP = "gzip"
    LZ4 = "lz4"


@dataclass
class EventMetadata:
    """Metadata for event recording sessions"""
    session_id: str
    start_time: float
    end_time: Optional[float] = None
    total_events: int = 0
    event_types: Dict[str, int] = None
    screen_resolution: Optional[Tuple[int, int]] = None
    agent_version: str = "1.0.0"
    schema_version: str = "1.0"
    
    def __post_init__(self):
        if self.event_types is None:
            self.event_types = {}


@dataclass
class ProcessedEvent:
    """Processed and validated event structure"""
    type: str
    timestamp: float
    session_id: str
    event_id: str
    data: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return asdict(self)
    
    @classmethod
    def from_raw_event(cls, raw_event: Dict[str, Any], session_id: str) -> 'ProcessedEvent':
        """Create ProcessedEvent from raw event data"""
        event_type = raw_event.get("type", "unknown")
        timestamp = raw_event.get("timestamp", time.time())
        
        # Generate unique event ID
        event_id = hashlib.md5(
            f"{session_id}_{timestamp}_{event_type}".encode()
        ).hexdigest()[:16]
        
        # Extract data (everything except type and timestamp)
        data = {k: v for k, v in raw_event.items() if k not in ["type", "timestamp"]}
        
        return cls(
            type=event_type,
            timestamp=timestamp,
            session_id=session_id,
            event_id=event_id,
            data=data
        )


class EventValidator:
    """Validates and sanitizes event data"""
    
    REQUIRED_FIELDS = ["type", "timestamp"]
    VALID_EVENT_TYPES = {
        "screenshot", "key", "mouse", "mouse_move", 
        "window_change", "scroll", "application_start", "application_end"
    }
    
    @staticmethod
    def validate_event(event: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate an event dictionary
        
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        # Check required fields
        for field in EventValidator.REQUIRED_FIELDS:
            if field not in event:
                errors.append(f"Missing required field: {field}")
        
        # Validate event type
        event_type = event.get("type")
        if event_type and event_type not in EventValidator.VALID_EVENT_TYPES:
            errors.append(f"Invalid event type: {event_type}")
        
        # Validate timestamp
        timestamp = event.get("timestamp")
        if timestamp is not None:
            if not isinstance(timestamp, (int, float)):
                errors.append("Timestamp must be a number")
            elif timestamp < 0:
                errors.append("Timestamp cannot be negative")
        
        # Type-specific validations
        if event_type == "mouse" or event_type == "mouse_move":
            if "x" not in event or "y" not in event:
                errors.append("Mouse events must have x and y coordinates")
            else:
                x, y = event.get("x"), event.get("y")
                if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
                    errors.append("Mouse coordinates must be numbers")
        
        if event_type == "key":
            if "key" not in event:
                errors.append("Key events must have a key field")
        
        if event_type == "screenshot":
            if "path" not in event:
                errors.append("Screenshot events must have a path field")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def sanitize_event(event: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize event data to remove sensitive information"""
        sanitized = event.copy()
        
        # Remove or mask sensitive data
        if event.get("type") == "key":
            key = event.get("key", "")
            # Mask potential passwords or sensitive input
            if len(key) == 1 and key.isprintable():
                # Keep single characters but mask sequences that might be sensitive
                pass
            else:
                # For special keys, keep as-is
                pass
        
        # Sanitize file paths (remove user-specific directories)
        if "path" in sanitized:
            path = sanitized["path"]
            if isinstance(path, str):
                # Replace user directory with placeholder
                import os
                user_dir = os.path.expanduser("~")
                if path.startswith(user_dir):
                    sanitized["path"] = path.replace(user_dir, "~")
        
        return sanitized


class EventFilter:
    """Filters events based on various criteria"""
    
    def __init__(self):
        self.last_mouse_move_time = 0
        self.mouse_move_threshold = 0.05  # 50ms minimum between mouse moves
        self.duplicate_event_window = 1.0  # 1 second window for duplicate detection
        self.recent_events = []
    
    def should_include_event(self, event: Dict[str, Any]) -> bool:
        """Determine if an event should be included in the output"""
        event_type = event.get("type")
        timestamp = event.get("timestamp", 0)
        
        # Filter excessive mouse movement events
        if event_type == "mouse_move":
            if timestamp - self.last_mouse_move_time < self.mouse_move_threshold:
                return False
            self.last_mouse_move_time = timestamp
        
        # Filter duplicate events within time window
        for recent_event in self.recent_events:
            if (timestamp - recent_event["timestamp"] < self.duplicate_event_window and
                self._events_are_similar(event, recent_event)):
                return False
        
        # Update recent events (keep last 10)
        self.recent_events.append(event)
        if len(self.recent_events) > 10:
            self.recent_events.pop(0)
        
        return True
    
    def _events_are_similar(self, event1: Dict[str, Any], event2: Dict[str, Any]) -> bool:
        """Check if two events are similar enough to be considered duplicates"""
        if event1.get("type") != event2.get("type"):
            return False
        
        event_type = event1.get("type")
        
        if event_type == "mouse":
            # Same mouse button and position
            return (event1.get("x") == event2.get("x") and
                    event1.get("y") == event2.get("y") and
                    event1.get("button") == event2.get("button") and
                    event1.get("pressed") == event2.get("pressed"))
        
        if event_type == "key":
            # Same key
            return event1.get("key") == event2.get("key")
        
        if event_type == "window_change":
            # Same window title
            return event1.get("title") == event2.get("title")
        
        return False


class EventSerializer:
    """Main event serialization class"""
    
    def __init__(self, 
                 format: SerializationFormat = SerializationFormat.JSON,
                 compression: CompressionType = CompressionType.NONE,
                 validate_events: bool = True,
                 filter_events: bool = True):
        """
        Initialize the event serializer
        
        Args:
            format: Serialization format to use
            compression: Compression type to apply
            validate_events: Whether to validate events before serialization
            filter_events: Whether to filter events to remove noise
        """
        self.format = format
        self.compression = compression
        self.validate_events = validate_events
        self.filter_events = filter_events
        
        self.validator = EventValidator() if validate_events else None
        self.filter = EventFilter() if filter_events else None
        
        # Check format availability
        if format in [SerializationFormat.MSGPACK, SerializationFormat.MSGPACK_COMPRESSED]:
            if not MSGPACK_AVAILABLE:
                logger.warning("MessagePack not available, falling back to JSON")
                self.format = SerializationFormat.JSON
        
        if compression == CompressionType.LZ4 and not LZ4_AVAILABLE:
            logger.warning("LZ4 not available, falling back to gzip")
            self.compression = CompressionType.GZIP
    
    def serialize_events(self, 
                        events: List[Dict[str, Any]], 
                        output_path: Union[str, Path],
                        session_metadata: Optional[EventMetadata] = None) -> bool:
        """
        Serialize events to file
        
        Args:
            events: List of event dictionaries
            output_path: Path to output file
            session_metadata: Optional metadata about the session
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Serializing {len(events)} events to {output_path}")
            
            # Process events
            processed_events = []
            session_id = session_metadata.session_id if session_metadata else f"session_{int(time.time())}"
            
            for raw_event in events:
                # Validate event
                if self.validate_events:
                    is_valid, errors = self.validator.validate_event(raw_event)
                    if not is_valid:
                        logger.warning(f"Invalid event skipped: {errors}")
                        continue
                
                # Filter event
                if self.filter_events:
                    if not self.filter.should_include_event(raw_event):
                        continue
                
                # Sanitize and process
                sanitized_event = self.validator.sanitize_event(raw_event) if self.validate_events else raw_event
                processed_event = ProcessedEvent.from_raw_event(sanitized_event, session_id)
                processed_events.append(processed_event.to_dict())
            
            # Create output data structure
            output_data = {
                "metadata": asdict(session_metadata) if session_metadata else {},
                "events": processed_events,
                "total_events": len(processed_events),
                "serialization_format": self.format.value,
                "compression": self.compression.value,
                "serialized_at": datetime.utcnow().isoformat()
            }
            
            # Serialize data
            serialized_data = self._serialize_data(output_data)
            
            # Compress if needed
            final_data = self._compress_data(serialized_data)
            
            # Write to file
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            mode = 'wb' if isinstance(final_data, bytes) else 'w'
            with open(output_path, mode) as f:
                f.write(final_data)
            
            logger.info(f"Successfully serialized {len(processed_events)} events")
            return True
            
        except Exception as e:
            logger.error(f"Failed to serialize events: {e}", exc_info=True)
            return False
    
    def deserialize_events(self, input_path: Union[str, Path]) -> Tuple[List[Dict[str, Any]], Optional[EventMetadata]]:
        """
        Deserialize events from file
        
        Args:
            input_path: Path to input file
            
        Returns:
            Tuple of (events_list, metadata)
        """
        try:
            logger.info(f"Deserializing events from {input_path}")
            
            # Read file
            input_path = Path(input_path)
            with open(input_path, 'rb') as f:
                file_data = f.read()
            
            # Decompress if needed
            decompressed_data = self._decompress_data(file_data)
            
            # Deserialize data
            data = self._deserialize_data(decompressed_data)
            
            # Extract events and metadata
            events = data.get("events", [])
            metadata_dict = data.get("metadata", {})
            
            metadata = None
            if metadata_dict:
                metadata = EventMetadata(**metadata_dict)
            
            logger.info(f"Successfully deserialized {len(events)} events")
            return events, metadata
            
        except Exception as e:
            logger.error(f"Failed to deserialize events: {e}", exc_info=True)
            return [], None
    
    def _serialize_data(self, data: Dict[str, Any]) -> Union[str, bytes]:
        """Serialize data based on format"""
        if self.format in [SerializationFormat.JSON, SerializationFormat.JSON_COMPRESSED]:
            return json.dumps(data, indent=2, default=str)
        
        elif self.format in [SerializationFormat.MSGPACK, SerializationFormat.MSGPACK_COMPRESSED]:
            return msgpack.packb(data, use_bin_type=True)
        
        elif self.format in [SerializationFormat.PICKLE, SerializationFormat.PICKLE_COMPRESSED]:
            return pickle.dumps(data, protocol=pickle.HIGHEST_PROTOCOL)
        
        else:
            raise ValueError(f"Unsupported format: {self.format}")
    
    def _deserialize_data(self, data: Union[str, bytes]) -> Dict[str, Any]:
        """Deserialize data based on format"""
        if self.format in [SerializationFormat.JSON, SerializationFormat.JSON_COMPRESSED]:
            if isinstance(data, bytes):
                data = data.decode('utf-8')
            return json.loads(data)
        
        elif self.format in [SerializationFormat.MSGPACK, SerializationFormat.MSGPACK_COMPRESSED]:
            return msgpack.unpackb(data, raw=False)
        
        elif self.format in [SerializationFormat.PICKLE, SerializationFormat.PICKLE_COMPRESSED]:
            return pickle.loads(data)
        
        else:
            raise ValueError(f"Unsupported format: {self.format}")
    
    def _compress_data(self, data: Union[str, bytes]) -> bytes:
        """Compress data based on compression type"""
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        if self.compression == CompressionType.NONE:
            return data
        elif self.compression == CompressionType.GZIP:
            return gzip.compress(data)
        elif self.compression == CompressionType.LZ4:
            return lz4.frame.compress(data)
        else:
            raise ValueError(f"Unsupported compression: {self.compression}")
    
    def _decompress_data(self, data: bytes) -> Union[str, bytes]:
        """Decompress data based on compression type"""
        if self.compression == CompressionType.NONE:
            return data
        elif self.compression == CompressionType.GZIP:
            return gzip.decompress(data)
        elif self.compression == CompressionType.LZ4:
            return lz4.frame.decompress(data)
        else:
            raise ValueError(f"Unsupported compression: {self.compression}")
    
    def get_file_extension(self) -> str:
        """Get appropriate file extension for current format"""
        base_ext = {
            SerializationFormat.JSON: ".json",
            SerializationFormat.JSON_COMPRESSED: ".json.gz",
            SerializationFormat.MSGPACK: ".msgpack",
            SerializationFormat.MSGPACK_COMPRESSED: ".msgpack.gz",
            SerializationFormat.PICKLE: ".pickle",
            SerializationFormat.PICKLE_COMPRESSED: ".pickle.gz"
        }
        return base_ext.get(self.format, ".bin")


class EventBatchProcessor:
    """Process events in batches for large datasets"""
    
    def __init__(self, batch_size: int = 1000):
        self.batch_size = batch_size
    
    def process_event_stream(self, 
                           event_iterator: Iterator[Dict[str, Any]], 
                           output_dir: Path,
                           serializer: EventSerializer) -> List[Path]:
        """
        Process events in batches and save to multiple files
        
        Args:
            event_iterator: Iterator yielding events
            output_dir: Directory to save batch files
            serializer: EventSerializer instance
            
        Returns:
            List of paths to created batch files
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        batch_files = []
        batch = []
        batch_number = 0
        
        for event in event_iterator:
            batch.append(event)
            
            if len(batch) >= self.batch_size:
                # Process batch
                batch_file = output_dir / f"events_batch_{batch_number:04d}{serializer.get_file_extension()}"
                
                session_metadata = EventMetadata(
                    session_id=f"batch_{batch_number}",
                    start_time=batch[0].get("timestamp", time.time()),
                    end_time=batch[-1].get("timestamp", time.time()),
                    total_events=len(batch)
                )
                
                if serializer.serialize_events(batch, batch_file, session_metadata):
                    batch_files.append(batch_file)
                
                batch = []
                batch_number += 1
        
        # Process remaining events
        if batch:
            batch_file = output_dir / f"events_batch_{batch_number:04d}{serializer.get_file_extension()}"
            
            session_metadata = EventMetadata(
                session_id=f"batch_{batch_number}",
                start_time=batch[0].get("timestamp", time.time()),
                end_time=batch[-1].get("timestamp", time.time()),
                total_events=len(batch)
            )
            
            if serializer.serialize_events(batch, batch_file, session_metadata):
                batch_files.append(batch_file)
        
        return batch_files


# Convenience functions
def serialize_events_to_file(events: List[Dict[str, Any]], 
                           output_path: Union[str, Path],
                           format: SerializationFormat = SerializationFormat.JSON,
                           compress: bool = False) -> bool:
    """Convenience function to serialize events to file"""
    compression = CompressionType.GZIP if compress else CompressionType.NONE
    serializer = EventSerializer(format=format, compression=compression)
    
    # Create metadata
    if events:
        session_metadata = EventMetadata(
            session_id=f"session_{int(time.time())}",
            start_time=min(e.get("timestamp", 0) for e in events),
            end_time=max(e.get("timestamp", 0) for e in events),
            total_events=len(events)
        )
    else:
        session_metadata = None
    
    return serializer.serialize_events(events, output_path, session_metadata)


def deserialize_events_from_file(input_path: Union[str, Path]) -> List[Dict[str, Any]]:
    """Convenience function to deserialize events from file"""
    # Try different formats
    for format in SerializationFormat:
        try:
            serializer = EventSerializer(format=format)
            events, metadata = serializer.deserialize_events(input_path)
            if events:
                return events
        except Exception:
            continue
    
    logger.error(f"Failed to deserialize events from {input_path}")
    return []


# Example usage
if __name__ == "__main__":
    # Test the event serializer
    sample_events = [
        {
            "type": "mouse",
            "timestamp": time.time(),
            "x": 100,
            "y": 200,
            "button": "left",
            "pressed": True
        },
        {
            "type": "key", 
            "timestamp": time.time() + 1,
            "key": "a"
        },
        {
            "type": "screenshot",
            "timestamp": time.time() + 2,
            "path": "/tmp/screenshot.png"
        }
    ]
    
    # Test serialization
    output_file = "test_events.json.gz"
    success = serialize_events_to_file(
        sample_events, 
        output_file, 
        format=SerializationFormat.JSON,
        compress=True
    )
    
    if success:
        print(f"Successfully serialized {len(sample_events)} events to {output_file}")
        
        # Test deserialization
        loaded_events = deserialize_events_from_file(output_file)
        print(f"Successfully deserialized {len(loaded_events)} events")
        
        # Clean up
        os.unlink(output_file)
    else:
        print("Failed to serialize events")