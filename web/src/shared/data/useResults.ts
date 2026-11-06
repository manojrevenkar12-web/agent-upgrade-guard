import { useCallback, useEffect, useState } from "react";
import type { Results } from "./types";

type Load = { status: "loading" } | { status: "error"; message: string } | { status: "ready"; data: Results };

export function useResults(): Load & { retry: () => void } {
  const [load, setLoad] = useState<Load>({ status: "loading" });
  const [attempt, setAttempt] = useState(0);
  const retry = useCallback(() => setAttempt((a) => a + 1), []);

  useEffect(() => {
    let alive = true;
    setLoad({ status: "loading" });
    fetch("./data.json")
      .then((r) => {
        if (!r.ok) throw new Error(`data.json answered ${r.status}. Run \`guard report\` to generate it.`);
        return r.json() as Promise<Results>;
      })
      .then((data) => alive && setLoad({ status: "ready", data }))
      .catch((e: Error) => alive && setLoad({ status: "error", message: e.message }));
    return () => {
      alive = false;
    };
  }, [attempt]);

  return { ...load, retry };
}
