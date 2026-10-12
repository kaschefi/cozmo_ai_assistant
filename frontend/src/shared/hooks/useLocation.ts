import { useState, useEffect } from 'react';

/**
 * Custom hook to manage standalone URL path navigation using the HTML5 History API.
 * Listens to browser back/forward navigation and updates the active path.
 */
export const useLocation = () => {
  const [path, setPath] = useState(window.location.pathname);

  useEffect(() => {
    const handlePopState = () => {
      setPath(window.location.pathname);
    };

    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  const navigate = (newPath: string) => {
    window.history.pushState({}, '', newPath);
    setPath(newPath);
  };

  return [path, navigate] as const;
};

export default useLocation;
