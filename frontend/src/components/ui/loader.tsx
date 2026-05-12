import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface LoaderProps {
  className?: string;
  message?: string;
}

export function Loader({ className, message }: LoaderProps) {
  return (
    <div className={cn("flex items-center gap-3 text-muted-foreground", className)}>
      <Loader2 className="h-5 w-5 animate-spin" />
      {message && <span className="text-sm italic">{message}</span>}
    </div>
  );
}
