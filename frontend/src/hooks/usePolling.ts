import { useEffect, useRef } from 'react';

interface PollingOptions {
  fn: () => void;
  interval: number;
  enabled: boolean;
  maxWaitMs?: number;
  onTimeout?: () => void;
}

export const usePolling = ({ fn, interval, enabled, maxWaitMs, onTimeout }: PollingOptions) => {
  const savedFn = useRef(fn);
  const savedOnTimeout = useRef(onTimeout);
  const timedOutRef = useRef(false);
  savedFn.current = fn;
  savedOnTimeout.current = onTimeout;

  useEffect(() => {
    if (!enabled) {
      timedOutRef.current = false;
      return;
    }

    timedOutRef.current = false;
    const start = Date.now();

    const timer = setInterval(() => {
      if (timedOutRef.current) {
        clearInterval(timer);
        return;
      }
      savedFn.current();
      if (maxWaitMs && Date.now() - start >= maxWaitMs) {
        timedOutRef.current = true;
        clearInterval(timer);
        savedOnTimeout.current?.();
      }
    }, interval);

    return () => clearInterval(timer);
  }, [interval, enabled, maxWaitMs]);
};
