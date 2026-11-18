import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  useRef,
} from "react";
import { get, errorText } from "./api/client";
const Context = createContext(null);
export function AppProvider({ children }) {
  const [epoch, setEpoch] = useState(0),
    [rates, setRates] = useState(null),
    [toasts, setToasts] = useState([]),
    [confirmation, setConfirmation] = useState(null);
  const timers = useRef([]);
  const notify = useCallback((text, type = "success") => {
    const id = Date.now() + Math.random();
    setToasts((a) => [...a, { id, text, type }]);
    timers.current.push(
      setTimeout(() => setToasts((a) => a.filter((x) => x.id !== id)), 5500),
    );
  }, []);
  const refresh = useCallback(() => setEpoch((x) => x + 1), []);
  const confirm = useCallback(
    (title, description) =>
      new Promise((resolve) =>
        setConfirmation({ title, description, resolve }),
      ),
    [],
  );
  useEffect(() => {
    let alive = true;
    get("/currencies")
      .then((x) => {
        if (alive) setRates(x);
      })
      .catch(() => {
        if (alive)
          setRates((previous) => ({
            ...previous,
            rates_stale: true,
            rates_fetch_failed: true,
          }));
      });
    return () => {
      alive = false;
    };
  }, [epoch]);
  useEffect(() => () => timers.current.forEach(clearTimeout), []);
  return (
    <Context.Provider
      value={{
        epoch,
        refresh,
        notify,
        rates,
        confirm,
        confirmation,
        setConfirmation,
        toasts,
      }}
    >
      {children}
    </Context.Provider>
  );
}
export const useApp = () => useContext(Context);
export function useResource(loader, deps = []) {
  const { epoch } = useApp();
  const [result, setResult] = useState({
    data: null,
    error: null,
    loading: true,
  });
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    let alive = true;
    setResult((x) => ({ ...x, error: null, loading: true }));
    Promise.resolve()
      .then(loader)
      .then((data) => {
        if (alive) setResult({ data, error: null, loading: false });
      })
      .catch((error) => {
        if (alive)
          setResult({ data: null, error: errorText(error), loading: false });
      });
    return () => {
      alive = false;
    };
  }, [epoch, retry, ...deps]);
  return { ...result, reload: () => setRetry((x) => x + 1) };
}
