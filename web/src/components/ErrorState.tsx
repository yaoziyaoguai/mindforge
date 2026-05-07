export function ErrorState({ message }: { message: string }) {
  return (
    <section className="rounded-md border border-red-200 bg-red-50 p-4 text-danger">
      <h2 className="font-semibold">Something needs attention</h2>
      <p className="mt-1 text-sm">{message}</p>
    </section>
  );
}
