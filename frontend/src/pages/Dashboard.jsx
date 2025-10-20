import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import CardEleicao from "../components/CardEleicao.jsx";
import { createElection, fetchElections } from "../services/api.js";

const Dashboard = () => {
  const [elections, setElections] = useState([]);
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({ title: "", description: "", candidates: "" });
  const [message, setMessage] = useState("");
  const navigate = useNavigate();

  const loadElections = async () => {
    try {
      const data = await fetchElections();
      setElections(data);
    } catch (error) {
      setMessage("Erro ao carregar eleições.");
    }
  };

  useEffect(() => {
    loadElections();
  }, []);

  const handleChange = (event) => {
    setForm((prev) => ({ ...prev, [event.target.name]: event.target.value }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setLoading(true);
    setMessage("");
    try {
      const candidates = form.candidates
        .split(",")
        .map((candidate) => candidate.trim())
        .filter(Boolean);
      if (!candidates.length) {
        setMessage("Informe ao menos um candidato.");
        return;
      }
      await createElection({
        title: form.title,
        description: form.description,
        candidates
      });
      setForm({ title: "", description: "", candidates: "" });
      setMessage("Eleição criada com sucesso!");
      await loadElections();
    } catch (error) {
      setMessage(error.response?.data?.message || "Erro ao criar eleição.");
    } finally {
      setLoading(false);
    }
  };

  const handleVote = (id) => navigate(`/votacao/${id}`);
  const handleResults = (id) => navigate(`/resultado/${id}`);

  return (
    <section className="space-y-8">
      <div className="rounded-2xl border border-slate-800 bg-slate-950/40 p-6">
        <h2 className="text-lg font-semibold text-white">Registrar nova eleição</h2>
        <form onSubmit={handleSubmit} className="mt-4 space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-300">Título</label>
            <input
              type="text"
              name="title"
              value={form.title}
              onChange={handleChange}
              className="mt-1 w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white focus:border-primary focus:outline-none"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-300">Descrição</label>
            <textarea
              name="description"
              value={form.description}
              onChange={handleChange}
              className="mt-1 w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white focus:border-primary focus:outline-none"
              rows="3"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-300">
              Candidatos (separe por vírgula)
            </label>
            <input
              type="text"
              name="candidates"
              value={form.candidates}
              onChange={handleChange}
              className="mt-1 w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white focus:border-primary focus:outline-none"
              required
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-blue-600 disabled:bg-blue-400"
          >
            {loading ? "Criando..." : "Criar eleição"}
          </button>
        </form>
        {message && <p className="mt-4 text-sm text-slate-300">{message}</p>}
      </div>

      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-white">Eleições disponíveis</h2>
          <button
            type="button"
            onClick={loadElections}
            className="rounded-md border border-slate-700 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-slate-200 hover:border-primary hover:text-primary"
          >
            Atualizar
          </button>
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          {elections.map((election) => (
            <CardEleicao
              key={election.id}
              election={election}
              onVote={handleVote}
              onResults={handleResults}
            />
          ))}
          {!elections.length && (
            <div className="rounded-xl border border-dashed border-slate-700 p-10 text-center text-sm text-slate-400">
              Nenhuma eleição cadastrada ainda.
            </div>
          )}
        </div>
      </div>
    </section>
  );
};

export default Dashboard;
