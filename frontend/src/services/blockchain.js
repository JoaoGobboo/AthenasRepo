import Web3 from "web3";

const CONTRACT_ADDRESS = import.meta.env.VITE_CONTRACT_ADDRESS;
const CONTRACT_ABI = import.meta.env.VITE_CONTRACT_ABI ? JSON.parse(import.meta.env.VITE_CONTRACT_ABI) : null;

export const getWeb3 = async () => {
  if (window.ethereum) {
    const web3 = new Web3(window.ethereum);
    return web3;
  }
  throw new Error("MetaMask não encontrada. Instale a extensão para continuar.");
};

export const connectWallet = async () => {
  const web3 = await getWeb3();
  await window.ethereum.request({ method: "eth_requestAccounts" });
  const accounts = await web3.eth.getAccounts();
  if (!accounts.length) {
    throw new Error("Nenhuma carteira disponível");
  }
  return accounts[0];
};

export const signNonce = async (walletAddress, nonce) => {
  const web3 = await getWeb3();
  const message = `Login nonce: ${nonce}`;
  const signature = await web3.eth.personal.sign(message, walletAddress, "");
  return signature;
};

export const generateNonce = () => {
  return Math.random().toString(36).substring(2, 10);
};

export const getContract = async () => {
  if (!CONTRACT_ADDRESS || !CONTRACT_ABI) {
    throw new Error("Contrato não configurado. Defina VITE_CONTRACT_ADDRESS e VITE_CONTRACT_ABI.");
  }
  const web3 = await getWeb3();
  return new web3.eth.Contract(CONTRACT_ABI, CONTRACT_ADDRESS);
};

const getActiveAccount = async () => {
  const accounts = await window.ethereum.request({ method: "eth_requestAccounts" });
  if (!accounts.length) {
    throw new Error("Nenhuma carteira conectada");
  }
  return accounts[0];
};

export const createElectionOnChain = async (title, candidates) => {
  const contract = await getContract();
  const from = await getActiveAccount();
  const receipt = await contract.methods.createElection(title, candidates).send({ from });
  return receipt.transactionHash;
};

export const voteOnChain = async (electionId, candidateIndex) => {
  const contract = await getContract();
  const from = await getActiveAccount();
  const receipt = await contract.methods.vote(electionId, candidateIndex).send({ from });
  return receipt.transactionHash;
};
