import os
import re

def extract_info_from_email(content):
    info = {
        "overview": [],
        "timeline": [],
        "risks": [],
        "impact": [],
        "status": []
    }

    # Overview: Project Alpha as an analytics dashboard
    overview_regex = r"Project Alpha has been officially greenlit! This is our\s+new customer-facing analytics dashboard"
    overview_match = re.search(overview_regex, content)
    if overview_match:
        info["overview"].append("Project Alpha is a new customer-facing analytics dashboard designed to replace the legacy reporting system.")
    
    # Tech Stack (part of overview) - REVISED AGAIN for sentence-based extraction
    tech_stack = []
    time_series_match = re.search(r"We're going with (.*?)\s+for the time-series data", content)
    if time_series_match:
        tech_stack.append(time_series_match.group(1).strip())
    
    api_match = re.search(r"API will be built with (.*?)\s+\(Python\)", content)
    if api_match:
        tech_stack.append(api_match.group(1).strip())
    
    frontend_match = re.search(r"Frontend will use (.*?)\s+with the new charting library", content)
    if frontend_match:
        tech_stack.append(frontend_match.group(1).strip())
    
    if tech_stack:
        info["overview"].append(f"Key technologies include: {', '.join(tech_stack)}.")

    # Budget (initial extraction was incomplete)
    budget_regex = r"Budget has been approved for (.*?)(?=\n|$)"
    budget_match = re.search(budget_regex, content)
    if budget_match:
        info["overview"].append(f"Approved budget: {budget_match.group(1).strip()}. ")
    
    # Timeline (initial extraction was incomplete)
    timeline_regex = r"Timeline:\s*(.*?)(?=\n\n|\Z)"
    timeline_section_match = re.search(timeline_regex, content, re.DOTALL)
    if timeline_section_match:
        timeline_details = timeline_section_match.group(1).strip().split('\n')
        info["timeline"].extend([line.strip().replace('- ', '') for line in timeline_details if line.strip()])

    return infodef 