import { useEffect, useState } from "react";
import { fetchElections, fetchResults } from "../services/api.js";
import { loadCache, saveCache } from "../utils/cache.js";

const Auditoria = () => {
  const [records, setRecords] = useState([]);
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const formatRecord = (result) => ({
      id: result.election.id,
      title: result.election.title,
      candidates: result.results,
      source: result.source,
      blockchain: result.blockchain,
    });

    const loadAuditTrail = async () => {
      try {
        const cached = loadCache("audit-records", 60);
        if (cached) {
          setRecords(cached);
        }
        const elections = await fetchElections();
        const baseResults = await Promise.all(
          elections.map(async (election) => {
            try {
              const result = await fetchResults(election.id, { includeBlockchain: false });
              return formatRecord(result);
            } catch (error) {
              return {
                id: election.id,
                title: election.title,
                candidates: [],
                source: "indisponível",
                blockchain: { status: "error" }
              };
            }
          })
        );
        setRecords(baseResults);
        saveCache("audit-records", baseResults);

        elections.forEach(async (election) => {
          try {
            const chainResult = await fetchResults(election.id);
            if (chainResult.source === "blockchain") {
              setRecords((prev) => {
                const next = prev.map((record) =>
                  record.id === election.id ? formatRecord(chainResult) : record
                );
                saveCache("audit-records", next);
                return next;
              });
            }
          } catch (error) {
            // Ignore individual blockchain errors for audit refresh
          }
        });
      } catch (error) {
        setStatus("Falha ao carregar dados de auditoria.");
      } finally {
        setLoading(false);
      }
    };
    loadAuditTrail();
  }, []);

  if (loading) {
    return (
      <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-6 text-sm text-slate-300">
        Carregando informações de auditoria...
      </div>
    );
  }

  if (status) {
    return (
      <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-6 text-sm text-slate-300">
        {status}
      </div>
    );
  }

  return (
    <section className="space-y-4">
      <header>
        <h2 className="text-2xl font-semibold text-white">Auditoria de eleições</h2>
        <p className="mt-2 text-sm text-slate-300">
          Visualize o histórico consolidado de votos registrado na blockchain.
        </p>
      </header>

      {records.map((record) => (
        <article
          key={record.id}
          className="rounded-xl border border-slate-800 bg-slate-950/40 p-6 text-sm text-slate-300"
        >
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold text-white">{record.title}</h3>
              <p className="mt-1 text-xs uppercase tracking-wide text-slate-400">
                Fonte: {record.source === "blockchain" ? "Blockchain Ethereum" : "Base de dados"}
                {record.source !== "blockchain" && record.blockchain?.status !== "disabled" && (
                  <span> (sincronizando blockchain...)</span>
                )}
              </p>
            </div>
            <span className="rounded-full bg-primary/10 px-3 py-1 text-xs font-semibold text-primary">
              {record.candidates.length} candidatos
            </span>
          </div>
          <ul className="mt-4 space-y-2">
            {record.candidates.map((candidate) => (
              <li
                key={`${record.id}-${candidate.candidate}`}
                className="flex items-center justify-between rounded-lg border border-slate-800 px-4 py-2"
              >
                <span>{candidate.candidate}</span>
                <span className="font-semibold">{candidate.votes} voto(s)</span>
              </li>
            ))}
            {!record.candidates.length && (
              <li className="rounded-lg border border-dashed border-slate-700 px-4 py-3 text-center text-slate-500">
                Nenhum voto registrado ainda.
              </li>
            )}
          </ul>
        </article>
      ))}

      {!records.length && (
        <div className="rounded-xl border border-dashed border-slate-700 p-10 text-center text-sm text-slate-400">
          Nenhuma eleição cadastrada para auditoria.
        </div>
      )}
    </section>
  );
};

export default Auditoria;
