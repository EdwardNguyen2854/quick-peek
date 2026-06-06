export default function HtmlViewer({ url }: { url: string }) {
  return (
    <iframe
      className="html-frame"
      src={url}
      title="HTML Preview"
    />
  );
}