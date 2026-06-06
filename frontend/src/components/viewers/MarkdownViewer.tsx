import { useEffect, useState } from 'react';

export default function MarkdownViewer({ url }: { url: string }) {
  const [html, setHtml] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetch(url)
      .then((r) => {
        if (!r.ok) throw new Error('Failed to load');
        return r.text();
      })
      .then((content) => {
        setHtml(content);
        setLoading(false);
      })
      .catch(() => {
        setHtml('<p>Cannot load preview</p>');
        setLoading(false);
      });
  }, [url]);

  if (loading) {
    return <div className="markdown-viewer loading">Loading...</div>;
  }

  return <div className="markdown-viewer" dangerouslySetInnerHTML={{ __html: html }} />;
}