import { useEffect, useState } from 'react';

export default function TextViewer({ url }: { url: string }) {
  const [content, setContent] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetch(url)
      .then((r) => {
        if (!r.ok) throw new Error('Failed to load');
        return r.text();
      })
      .then(setContent)
      .catch(() => setContent('Cannot load file'))
      .finally(() => setLoading(false));
  }, [url]);

  if (loading) {
    return <div className="text-viewer loading">Loading...</div>;
  }

  return <pre className="text-viewer">{content}</pre>;
}