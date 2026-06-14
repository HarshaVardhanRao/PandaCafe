import axios from "axios";
import { usePOSStore } from "./store";

const BACKEND_HOST = window.location.hostname ? `${window.location.hostname}:8000` : "localhost:8000";
export const API_URL = `http://${BACKEND_HOST}/api/v1`;

const api = axios.create({
  baseURL: API_URL,
});

api.interceptors.request.use((config) => {
  const token = usePOSStore.getState().token;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export default api;
