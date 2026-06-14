import React from "react";
import ReactDOM from "react-dom/client";
import "./index.css";
import Login from "./components/Login";
import Dashboard from "./components/Dashboard";
import { usePOSStore } from "./store";

function App() {
  const token = usePOSStore((state) => state.token);
  return token ? <Dashboard /> : <Login />;
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);