# TODO: Refactor chatbot_enhanced.py

The backend has been refactored to use a client-server architecture with a standalone `server.py` process. The `chatbot_enhanced.py` file now needs to be updated to use this new architecture.

## Tasks:

1.  **Remove `UnifiedMCPBackend`:** The `UnifiedMCPBackend` class, which directly executes R scripts, should be removed from `chatbot_enhanced.py`.

2.  **Implement `MCPClient`:** A new `MCPClient` class should be implemented in `chatbot_enhanced.py`. This class will be responsible for:
    *   Starting and managing the `server.py` subprocess.
    *   Communicating with the server via JSON-RPC over stdin/stdout.
    *   Sending requests to the server to execute R tools.
    *   Parsing responses from the server.

3.  **Create Tool Wrapper Functions:** Wrapper functions should be created for each tool (`initialize_meta_analysis`, `upload_study_data`, `execute_r_code`, etc.) that use an instance of the `MCPClient` to call the backend.

4.  **Update `handle_multimodal_submit`:** The main chat handler function should be updated to:
    *   Use the new tool wrapper functions.
    *   Include the new `execute_r_code` tool in the list of tools available to the LangChain agent.


5.  **Update Main Execution Block:** The `if __name__ == "__main__":` block should be updated to call the `start_mcp_server` function on startup.
