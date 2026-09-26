const { contextBridge } = require("electron");

// The Electron renderer never talks to Supabase or Gemini directly -- it
// only ever calls the local FastAPI backend, which holds every credential.
contextBridge.exposeInMainWorld("workflowos", {
  backendUrl: process.env.WORKFLOWOS_BACKEND_URL || "http://127.0.0.1:8000",
});
