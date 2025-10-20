import { useState } from "react";
import { loginWithSignature } from "../services/api.js";
import { connectWallet, generateNonce, signNonce } from "../services/blockchain.js";

const Login = ({ onSuccess }) => {
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(false);

  const handleLogin = async () => {
    setLoading(true);
    setStatus("");
    try {
      const wallet = await connectWallet();
      const nonce = generateNonce();
      const signature = await signNonce(wallet, nonce);
      const response = await loginWithSignature({ walletAddress: wallet, signature, nonce });
      onSuccess({ accessToken: response.access_token, walletAddress: wallet });
      setStatus("Conexão estabelecida!");
    } catch (error) {
      setStatus(error.message || "Falha ao autenticar.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="mx-auto max-w-lg rounded-2xl border border-slate-800 bg-slate-950/40 p-8 shadow-xl">
      <h1 className="text-2xl font-semibold text-white">Sistema de Votação em Blockchain</h1>
      <p className="mt-2 text-sm text-slate-300">
        Autentique-se com a MetaMask para acessar o painel de eleições e registrar seus votos com
        transparência garantida pela blockchain.
      </p>
      <button
        type="button"
        onClick={handleLogin}
        disabled={loading}
        className="mt-6 w-full rounded-lg bg-primary px-4 py-3 text-sm font-semibold text-white hover:bg-blue-600 disabled:bg-blue-400"
      >
        {loading ? "Conectando carteira..." : "Entrar com MetaMask"}
      </button>
      {status && <p className="mt-4 text-sm text-slate-300">{status}</p>}
    </section>
  );
};

export default Login;
