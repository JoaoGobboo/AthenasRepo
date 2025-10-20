import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:5000/api/v1";

const api = axios.create({
  baseURL: API_BASE_URL
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("athenas-token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const loginWithSignature = async ({ walletAddress, signature, nonce }) => {
  const response = await api.post("/auth/login", { walletAddress, signature, nonce });
  return response.data;
};

export const fetchElections = async () => {
  const response = await api.get("/elections");
  return response.data.elections;
};

export const createElection = async (payload) => {
  const response = await api.post("/elections", payload);
  return response.data.election;
};

export const submitVote = async ({ electionId, candidateId }) => {
  const response = await api.post("/vote", { electionId, candidateId });
  return response.data;
};

export const fetchResults = async (id) => {
  const response = await api.get(`/elections/${id}/results`);
  return response.data;
};

export default api;
