import json
import requests
from typing import Dict, Any
from .token_store import token_store

def _get_token_or_error(session_id: str):
    token = token_store.get_access_token(session_id)
    if not token:
        return None, json.dumps({"error": "No  token for session", "session_id": session_id})
    return token, None

def get_current_user_info(session_id: str) -> str:
    token, err = _get_token_or_error(session_id)
    if err: return err
    url = "https://graph.microsoft.com/v1.0/me"
    headers = {"Authorization": f"Bearer {token}", "Accept": "text/html, application/json"}
    resp = requests.get(url, headers=headers)
    if resp.status_code == 200:
        u = resp.json()
        return json.dumps({
            "success": True,
            "user": {
                "displayName": u.get("displayName"),
                "userPrincipalName": u.get("userPrincipalName"),
                "jobTitle": u.get("jobTitle"),
                "department": u.get("department"),
                "id": u.get("id"),
            }
        })
    return json.dumps({
        "error": f"Graph error {resp.status_code}",
        "message": resp.text
    })

def list_users(session_id: str) -> str:
    token, err = _get_token_or_error(session_id)
    if err: return err
    url = "https://graph.microsoft.com/v1.0/users?$top=5"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    resp = requests.get(url, headers=headers)
    if resp.status_code == 200:
        data = resp.json()
        return json.dumps({
            "success": True,
            "count": len(data.get("value", [])),
            "users": [
                {
                    "displayName": u.get("displayName"),
                    "userPrincipalName": u.get("userPrincipalName"),
                    "id": u.get("id")
                } for u in data.get("value", [])
            ]
        })
    elif resp.status_code in (401, 403):
        return json.dumps({
            "error": "Insufficient permissions or token invalid",
            "status": resp.status_code,
            "hint": "Ensure User.Read.All consent is granted" if resp.status_code == 403 else "Re-login"
        })
    return json.dumps({"error": f"Graph error {resp.status_code}", "message": resp.text})

def get_sharepoint_site(session_id: str, site_url: str = None) -> str:
    """
    Get SharePoint site information by URL or use default site.
    """
    token, err = _get_token_or_error(session_id)
    if err: return err
    
    # Default to your specific SharePoint site
    if not site_url:
        site_url = "YOUR_DEFAULT_SHAREPOINT_SITE_URL_HERE"
    
    # Extract hostname and site path from URL
    try:
        from urllib.parse import urlparse
        parsed = urlparse(site_url)
        hostname = parsed.netloc
        
        # Extract site path (remove /SitePages and everything after)
        path_parts = parsed.path.split('/')
        site_path_parts = []
        for part in path_parts:
            if part and part.lower() not in ['sitepages', 'siteassets', 'shared documents']:
                site_path_parts.append(part)
            else:
                break
        site_path = '/' + '/'.join(site_path_parts) if site_path_parts else ''
        
        # Construct the Graph API URL for the site
        # Format: /sites/{hostname}:/{site-path}
        if site_path:
            graph_url = f"https://graph.microsoft.com/v1.0/sites/{hostname}:{site_path}"
        else:
            graph_url = f"https://graph.microsoft.com/v1.0/sites/{hostname}"
            
    except Exception as e:
        return json.dumps({
            "error": "Invalid SharePoint URL",
            "details": str(e),
            "example": "YOUR_DEFAULT_SHAREPOINT_SITE_URL_HERE"
        })
    
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    resp = requests.get(graph_url, headers=headers)
    
    if resp.status_code == 200:
        site_data = resp.json()
        return json.dumps({
            "success": True,
            "site": {
                "id": site_data.get("id"),
                "name": site_data.get("name"),
                "displayName": site_data.get("displayName"),
                "webUrl": site_data.get("webUrl"),
                "description": site_data.get("description"),
                "createdDateTime": site_data.get("createdDateTime"),
                "lastModifiedDateTime": site_data.get("lastModifiedDateTime"),
                "siteCollection": {
                    "hostname": site_data.get("siteCollection", {}).get("hostname"),
                    "dataLocationCode": site_data.get("siteCollection", {}).get("dataLocationCode"),
                    "root": site_data.get("siteCollection", {}).get("root")
                }
            },
            "graph_api_url": graph_url
        })
    elif resp.status_code == 403:
        return json.dumps({
            "error": "Insufficient permissions to access SharePoint site",
            "status": resp.status_code,
            "hint": "Ensure Sites.Read.All or Sites.ReadWrite.All permission is granted",
            "required_permissions": ["Sites.Read.All", "Sites.ReadWrite.All"],
            "attempted_url": graph_url
        })
    elif resp.status_code == 404:
        return json.dumps({
            "error": "SharePoint site not found",
            "status": resp.status_code,
            "attempted_url": graph_url,
            "hint": "Check if the site URL is correct and you have access"
        })
    else:
        return json.dumps({
            "error": f"Graph API error {resp.status_code}",
            "message": resp.text,
            "attempted_url": graph_url
        })

def get_sharepoint_site_lists(session_id: str, site_id: str = None) -> str:
    """
    Get lists from a SharePoint site. If site_id is not provided, 
    it will first get the default site and then its lists.
    """
    token, err = _get_token_or_error(session_id)
    if err: return err
    
    # If no site_id provided, get the default site first
    if not site_id:
        site_result = get_sharepoint_site(session_id)
        try:
            site_data = json.loads(site_result)
            if site_data.get("success"):
                site_id = site_data["site"]["id"]
            else:
                return site_result  # Return the error from get_sharepoint_site
        except:
            return json.dumps({"error": "Failed to get default site"})
    
    # Get lists from the site
    url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    resp = requests.get(url, headers=headers)
    
    if resp.status_code == 200:
        lists_data = resp.json()
        return json.dumps({
            "success": True,
            "site_id": site_id,
            "count": len(lists_data.get("value", [])),
            "lists": [
                {
                    "id": lst.get("id"),
                    "name": lst.get("name"),
                    "displayName": lst.get("displayName"),
                    "webUrl": lst.get("webUrl"),
                    "createdDateTime": lst.get("createdDateTime"),
                    "list": {
                        "template": lst.get("list", {}).get("template"),
                        "hidden": lst.get("list", {}).get("hidden")
                    }
                } for lst in lists_data.get("value", [])
            ]
        })
    else:
        return json.dumps({
            "error": f"Failed to get site lists",
            "status": resp.status_code,
            "message": resp.text
        })

# Tool tanımları (Azure AI Agents format)
graph_api_tools = [
    {
        "type": "function",
        "function": {
            "name": "get_current_user_info",
            "description": "Get current signed-in user's profile",
            "parameters": {
                "type": "object",
                "properties": {
                    "session_id": {"type": "string", "description": "Session ID"}
                },
                "required": ["session_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_sharepoint_site",
            "description": "Get SharePoint site information by URL. Default: YOUR_DEFAULT_SHAREPOINT_SITE_URL_HERE",
            "parameters": {
                "type": "object",
                "properties": {
                    "session_id": {"type": "string", "description": "Session ID"},
                    "site_url": {
                        "type": "string", 
                        "description": "SharePoint site URL (optional, uses default if not provided)"
                    }
                },
                "required": ["session_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_sharepoint_site_lists",
            "description": "Get all lists from a SharePoint site",
            "parameters": {
                "type": "object",
                "properties": {
                    "session_id": {"type": "string", "description": "Session ID"},
                    "site_id": {
                        "type": "string", 
                        "description": "SharePoint site ID (optional, uses default site if not provided)"
                    }
                },
                "required": ["session_id"]
            }
        }
    }
]

function_map = {
    "get_current_user_info": get_current_user_info,
    "get_sharepoint_site": get_sharepoint_site,
    "get_sharepoint_site_lists": get_sharepoint_site_lists
}

def execute_tool_call(tool_call, session_id: str):
    import json as _json
    fn_name = tool_call.function.name
    if fn_name not in function_map:
        return _json.dumps({"error": f"Unknown function: {fn_name}"})
    args = {}
    if tool_call.function.arguments:
        try:
            args = _json.loads(tool_call.function.arguments)
        except Exception:
            pass
    args["session_id"] = session_id
    return function_map[fn_name](**args)