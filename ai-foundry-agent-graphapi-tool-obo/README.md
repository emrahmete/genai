# AI Foundry Agent with Microsoft Graph OBO Authentication

A Flask-based web application that demonstrates Azure AI Agents integration with Microsoft Graph API using OAuth 2.0 On-Behalf-Of (OBO) flow for delegated permissions.

## 🌟 Features 

- **Azure AI Agents Integration**: Uses Azure AI Foundry to create intelligent agents
- **Microsoft Graph API Integration**: Accesses user data and SharePoint sites with delegated permissions
- **Secure Token Management**: In-memory token storage with session management
- **Interactive Web UI**: Clean, responsive interface for agent interactions
- **OAuth 2.0 Authentication**: Implements secure authentication flow with MSAL

## 🏗️ Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Browser   │────▶│ Flask App   │────▶│ Azure AD    │
└─────────────┘     └─────────────┘     └─────────────┘
                            │
                            ├────────────▶ Microsoft Graph API
                            │
                            └────────────▶ Azure AI Foundry
```

## 📁 Project Structure

```
project/
├── .env                    # Environment configuration
├── app/
│   ├── agent_runner.py    # AI Agent execution logic
│   ├── graph_tools.py     # Microsoft Graph API tools
│   ├── server.py          # Flask server and routes
│   └── token_store.py     # Token management
└── static/
    └── index.html         # Web UI
```

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- Azure subscription
- Azure AD app registration
- Azure AI Foundry resource

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd project
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install flask msal requests azure-identity azure-ai-agents python-dotenv
```

### Configuration

1. Create an Azure AD app registration:
   - Go to [Azure Portal](https://portal.azure.com)
   - Navigate to Azure Active Directory > App registrations
   - Create new registration
   - Add redirect URI: `http://localhost:5000/callback`
   - Create a client secret
   - Grant API permissions: `User.Read`, `Sites.Read.All` (optional)

2. Set up Azure AI Foundry:
   - Create an AI Foundry resource in Azure
   - Note the endpoint URL

3. Configure environment variables in `.env`:
```env
CLIENT_ID=your-app-client-id
CLIENT_SECRET=your-app-client-secret
TENANT_ID=your-tenant-id
REDIRECT_URI=http://localhost:5000/callback
GRAPH_SCOPES=User.Read Sites.Read.All
AI_FOUNDRY_ENDPOINT=https://your-resource.services.ai.azure.com/api/projects/your-project
FLASK_SECRET_KEY=your-flask-secret-key
```

### Running the Application

```bash
python -m app.server
```

Navigate to `http://localhost:5000` in your browser.

## 💡 Usage

1. **Login**: Click login to authenticate with your Microsoft account
2. **Enter Prompt**: Type your request (e.g., "Get my user info", "Show my SharePoint site")
3. **Run Agent**: The AI agent will process your request and call appropriate Graph API endpoints
4. **View Results**: See the formatted response from the agent

### Example Prompts

- "Get my user information"
- "Show details about my SharePoint site"
- "List the document libraries in my SharePoint site"

## 🔧 Available Graph API Functions

### get_current_user_info
Retrieves the current user's profile information including display name, email, job title, and department.

### get_sharepoint_site
Fetches SharePoint site details. Default site: `Your sharepoint site URL`

### get_sharepoint_site_lists
Lists all document libraries and lists in a SharePoint site.

## 🔒 Security Considerations

⚠️ **This is a demo application. For production use:**

- Replace in-memory token storage with secure persistent storage (Redis, Azure Cache)
- Implement proper token encryption
- Add CSRF protection
- Use HTTPS in production
- Implement proper session management
- Add rate limiting
- Validate and sanitize all inputs

## 🛠️ Development

### Adding New Graph API Functions

1. Add the function in `app/graph_tools.py`:
```python
def your_new_function(session_id: str, param: str) -> str:
    token, err = _get_token_or_error(session_id)
    if err: return err
    # Your Graph API call here
```

2. Register the function in `graph_api_tools` list and `function_map` dictionary

3. The AI agent will automatically have access to the new function

### Customizing the AI Agent

Modify the agent instructions in `app/agent_runner.py`:
```python
agent = client.create_agent(
    model=model,
    name="your-agent-name",
    instructions="Your custom instructions here",
    tools=graph_api_tools
)
```

## 📝 License

This project is provided as a demonstration. Please ensure you comply with Microsoft's terms of service when using Graph API and Azure services.

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## ⚠️ Important Notes

- **Never commit `.env` file to version control** - it contains sensitive credentials
- The default SharePoint site URL in the code should be updated to your own
- Ensure proper API permissions are granted in Azure AD for all Graph API calls
- Monitor Azure AI Foundry usage to avoid unexpected costs

## 🐛 Troubleshooting

### Common Issues

1. **"No token for session" error**: User needs to re-authenticate
2. **403 Forbidden on Graph API**: Check API permissions in Azure AD
3. **Agent not responding**: Verify AI Foundry endpoint and credentials
4. **Authentication loop**: Clear browser cookies and session

### Debug Mode

The application runs in debug mode by default. For production:
```python
app.run(port=5000, debug=False)
```

## 📞 Support

For issues and questions:
- Check Azure AI Foundry documentation
- Review Microsoft Graph API documentation
- Ensure all prerequisites are properly configured