export default function DocViewer({ url }: { url: string }) {
  return (
    <iframe
      className="pdf-frame"
      src={url}
      title="Document Preview"
    />
  );
}