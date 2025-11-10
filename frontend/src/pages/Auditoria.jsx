import { useEffect, useState } from "react";
import useElectionsStore from "../store/useElectionsStore.js";
import useResultsStore from "../store/useResultsStore.js";

const Auditoria = () => {
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(true);

  const elections = useElectionsStore((state) => state.elections);
  const fetchElections = useElectionsStore((state) => state.fetchElections);
  const items = useResultsStore((state) => state.items);
  const loadingChain = useResultsStore((state) => state.loadingChain);
  const fetchResult = useResultsStore((state) => state.fetchResult);

  useEffect(() => {
    let active = true;
    const load = async () => {
      setStatus("");
      setLoading(true);
      try {
        const list = await fetchElections();
        if (!active) {
          return;
        }
        await Promise.all(
          list.map(async (election) => {
            try {
              await fetchResult(election.id);
            } catch (error) {
              if (active) {
                setStatus("Falha ao carregar dados de auditoria.");
              }
            }
          })
        );
      } catch (error) {
        if (active) {
          setStatus("Falha ao carregar dados de auditoria.");
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    };
    load();
    return () => {
      active = false;
    };
  }, [fetchElections, fetchResult]);

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

  const records = elections.map((election) => {
    const entry = items[election.id];
    const result = entry?.chain?.data || entry?.db?.data;
    return {
      id: election.id,
      title: election.title,
      source: result?.source || "database",
      blockchain: result?.blockchain,
      candidates: result?.results || election.candidates || [],
      syncing: result?.source !== "blockchain" && loadingChain[election.id]
    };
  });

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
                {record.syncing && <span> (sincronizando blockchain...)</span>}
              </p>
            </div>
            <span className="rounded-full bg-primary/10 px-3 py-1 text-xs font-semibold text-primary">
              {record.candidates.length} candidatos
            </span>
          </div>
          <ul className="mt-4 space-y-2">
            {record.candidates.map((candidate) => (
              <li
                key={`${record.id}-${candidate.candidate || candidate.name}`}
                className="flex items-center justify-between rounded-lg border border-slate-800 px-4 py-2"
              >
                <span>{candidate.candidate || candidate.name}</span>
                <span className="font-semibold">{candidate.votes ?? 0} voto(s)</span>
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
