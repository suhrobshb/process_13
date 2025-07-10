import { Link } from "wouter";
import { Button } from "@/components/ui/button";
import { AlertTriangle } from "lucide-react";

export default function NotFoundPage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-background text-foreground">
      <div className="text-center p-8 max-w-md">
        <AlertTriangle className="mx-auto h-24 w-24 text-destructive mb-6" />
        <h1 className="text-6xl font-bold text-destructive">404</h1>
        <h2 className="mt-4 text-2xl font-semibold tracking-tight">
          Page Not Found
        </h2>
        <p className="mt-2 text-muted-foreground">
          Sorry, the page you are looking for does not exist or has been moved.
        </p>
        <div className="mt-8">
          <Link href="/">
            <Button>Go Back to Dashboard</Button>
          </Link>
        </div>
      </div>
    </div>
  );
}
