import { useEffect, useRef } from 'react';

interface PollingOptions {
  fn: () => void;
  interval: number;
  enabled: boolean;
}

export const usePolling = ({ fn, interval, enabled }: PollingOptions) => {
  const savedFn = useRef(fn);
  savedFn.current = fn;

  useEffect(() => {
    if (!enabled) return;
    const timer = setInterval(() => savedFn.current(), interval);
    return () => clearInterval(timer);
  }, [interval, enabled]);
};
