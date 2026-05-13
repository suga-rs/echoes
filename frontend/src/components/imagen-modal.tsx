"use client";

import Image from "next/image";
import {
  Dialog,
  DialogContent,
} from "@/components/ui/dialog";

interface ImagenModalProps {
  src: string;
  open: boolean;
  onClose: () => void;
}

export function ImagenModal({ src, open, onClose }: ImagenModalProps) {
  return (
    <Dialog open={open} onOpenChange={(isOpen) => { if (!isOpen) onClose(); }}>
      <DialogContent className="max-w-fit border-0 bg-transparent p-0 shadow-none [&>button]:text-white [&>button]:opacity-80 [&>button]:hover:opacity-100">
        <div className="relative max-h-[90vh] max-w-[90vw]">
          <Image
            src={src}
            alt="Imagen de escena ampliada"
            width={1024}
            height={1024}
            className="rounded-lg object-contain max-h-[90vh] max-w-[90vw] w-auto h-auto"
            unoptimized
          />
        </div>
      </DialogContent>
    </Dialog>
  );
}
