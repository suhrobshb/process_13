#!/usr/bin/env python3
"""
AI Engine - Departmental Workflow Examples
==========================================

This script provides a library of comprehensive, real-world workflow examples
tailored for various professional departments. It demonstrates how the AI Engine's
capabilities (Desktop/Browser Automation, RAG, LLM, Decision Logic) can be
combined to automate complex business processes.

Each workflow is structured as a series of "action step boxes," complete with
inputs, processes, and outputs, illustrating the flow of data and logic.

Usage:
    python demo_department_workflows.py <department> <workflow_name>

Example:
    python demo_department_workflows.py accounting invoice_processing
    python demo_department_workflows.py legal contract_review
"""

import json
import sys
import argparse

# -------------------------------------------------------------------- #
# Workflow Definitions
# -------------------------------------------------------------------- #

DEPARTMENT_WORKFLOWS = {
    "accounting": {
        "invoice_processing": {
            "name": "Automated Invoice Processing",
            "description": "A workflow to receive, analyze, and process vendor invoices from email, with approval routing.",
            "steps": [
                {
                    "id": "step1_monitor_inbox",
                    "type": "llm",
                    "params": {
                        "inputs": ["Outlook/Gmail Inbox Stream"],
                        "process": "AI monitors the 'invoices@company.com' inbox for new emails with PDF attachments and a subject line containing 'Invoice'.",
                        "outputs": ["email_content", "invoice_pdf_attachment"]
                    }
                },
                {
                    "id": "step2_extract_invoice_data",
                    "type": "rag_decision",
                    "params": {
                        "inputs": ["${step1_monitor_inbox.invoice_pdf_attachment}"],
                        "process": "Using RAG, AI analyzes the invoice PDF. It queries a knowledge base of past vendor invoices to understand the specific layout, then extracts key fields: 'invoice_number', 'vendor_name', 'amount_due', 'due_date', and 'line_items'.",
                        "outputs": ["structured_invoice_data"]
                    }
                },
                {
                    "id": "step3_validate_invoice",
                    "type": "decision",
                    "params": {
                        "inputs": ["${step2_extract_invoice_data.structured_invoice_data}"],
                        "process": "The system validates the extracted data. It checks if 'amount_due' is a valid number and if 'vendor_name' exists in the internal vendor database.",
                        "scenarios": [
                            {"name": "is_valid", "condition": "data_is_clean and vendor_exists"},
                            {"name": "is_invalid", "condition": "not (data_is_clean and vendor_exists)"}
                        ],
                        "outputs": ["validation_status"]
                    }
                },
                {
                    "id": "step4_approval_routing",
                    "type": "decision",
                    "params": {
                        "inputs": ["${step2_extract_invoice_data.structured_invoice_data}"],
                        "process": "Based on company policy, the workflow decides if manager approval is needed. The condition is checked against the extracted invoice amount.",
                        "scenarios": [
                            {"name": "requires_approval", "condition": "${structured_invoice_data.amount_due} > 5000"},
                            {"name": "auto_approve", "condition": "${structured_invoice_data.amount_due} <= 5000"}
                        ],
                        "outputs": ["approval_path"]
                    }
                },
                {
                    "id": "step5_request_approval",
                    "type": "approval",
                    "params": {
                        "inputs": ["${step2_extract_invoice_data.structured_invoice_data}"],
                        "process": "If approval is required, this step sends a notification (e.g., via Slack or email) to the accounting manager with the invoice details and waits for their response.",
                        "outputs": ["approval_decision"]
                    }
                },
                {
                    "id": "step6_enter_into_accounting_software",
                    "type": "desktop",
                    "params": {
                        "inputs": ["${step2_extract_invoice_data.structured_invoice_data}"],
                        "process": "The AI Engine opens the desktop accounting software (e.g., QuickBooks Desktop), navigates to the 'Enter Bills' screen, and uses mouse clicks and keyboard typing to input the invoice data into the correct fields.",
                        "outputs": ["entry_confirmation_screenshot"]
                    }
                },
                {
                    "id": "step7_archive_invoice",
                    "type": "shell",
                    "params": {
                        "inputs": ["${step1_monitor_inbox.invoice_pdf_attachment}"],
                        "process": "The original invoice PDF is moved to a processed archive folder, renamed with the invoice number and vendor name for easy retrieval.",
                        "outputs": ["archive_log"]
                    }
                }
            ]
        }
    },
    "office_admin": {
        "meeting_coordination": {
            "name": "Intelligent Meeting Coordination",
            "description": "A workflow that schedules meetings, prepares materials, and sends summaries based on an email request.",
            "steps": [
                {
                    "id": "step1_parse_request",
                    "type": "llm",
                    "params": {
                        "inputs": ["Email from manager: 'Please schedule a 30-min kickoff meeting for Project Alpha with me, Sarah, and David from marketing next week.'"],
                        "process": "AI uses LLM to parse the email, identifying key entities: participants ('Sarah', 'David'), topic ('Project Alpha Kickoff'), and desired timeframe ('next week').",
                        "outputs": ["meeting_details_object"]
                    }
                },
                {
                    "id": "step2_check_calendars",
                    "type": "browser",
                    "params": {
                        "inputs": ["${step1_parse_request.meeting_details_object}"],
                        "process": "AI opens the company's web-based calendar (e.g., Google Calendar, Outlook 365), logs in, and navigates to the calendars of all participants to find common availability within the specified timeframe.",
                        "outputs": ["available_time_slots"]
                    }
                },
                {
                    "id": "step3_draft_invitation",
                    "type": "llm",
                    "params": {
                        "inputs": ["${step2_check_calendars.available_time_slots}", "${step1_parse_request.meeting_details_object}"],
                        "process": "AI drafts a meeting invitation email, suggesting the top 3 available time slots and including a brief agenda based on the meeting topic.",
                        "outputs": ["draft_invitation_email"]
                    }
                },
                {
                    "id": "step4_send_invitation",
                    "type": "desktop",
                    "params": {
                        "inputs": ["${step3_draft_invitation.draft_invitation_email}"],
                        "process": "AI opens the Outlook desktop client, creates a new meeting request, pastes the drafted content, adds the participants, and sends the invitation.",
                        "outputs": ["invitation_sent_confirmation"]
                    }
                },
                {
                    "id": "step5_prepare_materials",
                    "type": "rag_decision",
                    "params": {
                        "inputs": ["${step1_parse_request.meeting_details_object}"],
                        "process": "AI queries the company's knowledge base (e.g., SharePoint, Google Drive) for all documents related to 'Project Alpha'. It then uses an LLM to create a concise one-page summary and a list of key discussion points.",
                        "outputs": ["meeting_briefing_document"]
                    }
                }
            ]
        }
    },
    "legal": {
        "contract_review": {
            "name": "AI-Assisted Contract Review",
            "description": "A workflow that analyzes incoming contracts against company standards and flags risks.",
            "steps": [
                {
                    "id": "step1_ingest_contract",
                    "type": "rag_decision",
                    "params": {
                        "inputs": ["Third-party contract PDF"],
                        "process": "The user uploads a contract. The RAG engine ingests the document, making its text searchable and understandable.",
                        "outputs": ["contract_text", "data_source_id"]
                    }
                },
                {
                    "id": "step2_risk_analysis",
                    "type": "rag_decision",
                    "params": {
                        "inputs": ["${step1_ingest_contract.data_source_id}"],
                        "process": "AI queries the contract against a knowledge base of the company's legal playbook and standard clause library. It identifies non-standard clauses, ambiguous language, and missing protections.",
                        "query": "Compare this contract to our standard MSA template and identify all non-standard or high-risk clauses related to liability, indemnity, and termination.",
                        "outputs": ["risk_analysis_report"]
                    }
                },
                {
                    "id": "step3_generate_summary",
                    "type": "llm",
                    "params": {
                        "inputs": ["${step2_risk_analysis.risk_analysis_report}"],
                        "process": "The LLM generates a high-level executive summary of the identified risks, written in plain language for business stakeholders.",
                        "outputs": ["executive_summary"]
                    }
                },
                {
                    "id": "step4_decision_routing",
                    "type": "decision",
                    "params": {
                        "inputs": ["${step2_risk_analysis.risk_analysis_report}"],
                        "process": "The workflow routes the contract based on the severity of the identified risks.",
                        "scenarios": [
                            {"name": "high_risk", "condition": "risk_score > 8"},
                            {"name": "medium_risk", "condition": "risk_score > 4"},
                            {"name": "low_risk", "condition": "risk_score <= 4"}
                        ],
                        "outputs": ["routing_decision"]
                    }
                },
                {
                    "id": "step5_notify_legal_team",
                    "type": "http",
                    "params": {
                        "inputs": ["${step3_generate_summary.executive_summary}", "${step4_decision_routing.routing_decision}"],
                        "process": "Sends a notification to the legal team's Slack channel. High-risk contracts are flagged for immediate senior counsel review, while low-risk ones are added to the standard review queue.",
                        "outputs": ["slack_notification_confirmation"]
                    }
                }
            ]
        }
    },
    "banking": {
        "loan_prescreening": {
            "name": "Automated Loan Application Pre-Screening",
            "description": "A workflow that performs initial validation and risk assessment on new loan applications.",
            "steps": [
                {
                    "id": "step1_receive_application",
                    "type": "http",
                    "params": {
                        "inputs": ["Webhook from online loan application portal"],
                        "process": "A new loan application submitted online triggers the workflow via a webhook, providing a JSON payload with applicant data.",
                        "outputs": ["applicant_data"]
                    }
                },
                {
                    "id": "step2_data_extraction",
                    "type": "rag_decision",
                    "params": {
                        "inputs": ["${step1_receive_application.applicant_data.attached_documents}"],
                        "process": "If the application includes attachments (like pay stubs or bank statements in PDF), the RAG engine extracts and structures the financial data.",
                        "outputs": ["extracted_financials"]
                    }
                },
                {
                    "id": "step3_initial_checks",
                    "type": "parallel",
                    "params": {
                        "inputs": ["${step1_receive_application.applicant_data}"],
                        "process": "The engine performs several checks in parallel to save time.",
                        "sub_steps": [
                            {"id": "credit_check", "type": "http", "params": {"process": "Call external credit bureau API."}},
                            {"id": "internal_check", "type": "http", "params": {"process": "Check internal bank records for existing relationship."}},
                            {"id": "fraud_check", "type": "http", "params": {"process": "Run data against fraud detection service."}}
                        ],
                        "outputs": ["credit_score", "internal_status", "fraud_risk"]
                    }
                },
                {
                    "id": "step4_preliminary_decision",
                    "type": "rag_decision",
                    "params": {
                        "inputs": ["All previous outputs"],
                        "process": "An AI-powered decision step analyzes all collected data (application form, extracted financials, credit score, fraud risk) against the bank's internal lending policy documents.",
                        "query": "Based on the applicant's profile and our lending policy, should this application be 'pre-approved', 'rejected', or flagged for 'manual_review'?",
                        "outcomes": ["pre-approved", "rejected", "manual_review"],
                        "outputs": ["preliminary_decision"]
                    }
                },
                {
                    "id": "step5_update_crm",
                    "type": "browser",
                    "params": {
                        "inputs": ["${step4_preliminary_decision.preliminary_decision}", "${step1_receive_application.applicant_data}"],
                        "process": "AI opens the bank's web-based CRM, finds the applicant's record, and updates their status to reflect the pre-screening decision, adding a note with the AI's reasoning.",
                        "outputs": ["crm_update_confirmation"]
                    }
                }
            ]
        }
    },
    "back_office": {
        "data_migration": {
            "name": "Legacy System Data Migration",
            "description": "A workflow to migrate customer data from an old desktop application to a new web-based platform.",
            "steps": [
                {
                    "id": "step1_open_legacy_app",
                    "type": "desktop",
                    "params": {
                        "inputs": ["List of customer IDs to migrate"],
                        "process": "AI opens the legacy desktop CRM application.",
                        "actions": [
                            {"type": "activate_window", "title": "Legacy CRM v2.1"},
                            {"type": "wait", "duration": 2}
                        ],
                        "outputs": []
                    }
                },
                {
                    "id": "step2_loop_and_extract",
                    "type": "loop", # A conceptual step type for iteration
                    "params": {
                        "inputs": ["customer_id_list"],
                        "process": "For each customer ID in the list, perform a series of desktop actions to extract their data.",
                        "loop_steps": [
                            {"id": "search_customer", "type": "desktop", "params": {"actions": [{"type": "click", "image_path": "search_icon.png"}, {"type": "type", "text": "${current_customer_id}"}]}},
                            {"id": "copy_data", "type": "desktop", "params": {"actions": [{"type": "hotkey", "keys": ["ctrl", "a"]}, {"type": "hotkey", "keys": ["ctrl", "c"]}]}}
                        ],
                        "outputs": ["extracted_customer_data_list"]
                    }
                },
                {
                    "id": "step3_open_new_platform",
                    "type": "browser",
                    "params": {
                        "inputs": [],
                        "process": "AI opens a web browser and navigates to the new web-based CRM.",
                        "actions": [
                            {"type": "goto", "url": "https://new-crm.company.com/login"},
                            {"type": "fill", "selector": "#username", "text": "migration_bot"},
                            {"type": "fill", "selector": "#password", "text": "${CRM_PASSWORD}"},
                            {"type": "click", "selector": "#login-btn"}
                        ],
                        "outputs": []
                    }
                },
                {
                    "id": "step4_loop_and_enter_data",
                    "type": "loop",
                    "params": {
                        "inputs": ["${step2_loop_and_extract.extracted_customer_data_list}"],
                        "process": "For each extracted customer record, AI navigates to the 'New Customer' form in the web app and enters the data.",
                        "loop_steps": [
                            {"id": "navigate_to_form", "type": "browser", "params": {"actions": [{"type": "click", "selector": "#new-customer-link"}]}},
                            {"id": "fill_form", "type": "browser", "params": {"actions": [{"type": "fill", "selector": "#name", "text": "${current_customer.name}"}, {"type": "fill", "selector": "#email", "text": "${current_customer.email}"}]}},
                            {"id": "submit_form", "type": "browser", "params": {"actions": [{"type": "click", "selector": "button[type=submit]"}]}}
                        ],
                        "outputs": ["migration_log"]
                    }
                }
            ]
        }
    }
}


def main():
    """
    Command-line interface to display workflow examples.
    """
    parser = argparse.ArgumentParser(
        description="Display AI Engine workflow examples for different departments.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "department",
        nargs="?",
        choices=DEPARTMENT_WORKFLOWS.keys(),
        help="The department to show workflows for. If omitted, lists all departments."
    )
    parser.add_argument(
        "workflow_name",
        nargs="?",
        help="The specific workflow to display. If omitted, lists workflows for the selected department."
    )

    args = parser.parse_args()

    if not args.department:
        print("Available Departments:")
        for dept in DEPARTMENT_WORKFLOWS:
            print(f"- {dept}")
        return

    if args.department not in DEPARTMENT_WORKFLOWS:
        print(f"Error: Department '{args.department}' not found.")
        return

    department_workflows = DEPARTMENT_WORKFLOWS[args.department]

    if not args.workflow_name:
        print(f"Available Workflows for '{args.department}':")
        for name in department_workflows:
            print(f"- {name}")
        return

    if args.workflow_name not in department_workflows:
        print(f"Error: Workflow '{args.workflow_name}' not found in department '{args.department}'.")
        return

    workflow = department_workflows[args.workflow_name]
    print(json.dumps(workflow, indent=4))


if __name__ == "__main__":
    main()
