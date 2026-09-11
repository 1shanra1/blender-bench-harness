import { cn } from "cn"

function AspectRatio({
  ratio,
  style,
  className,
  ...props
}: React.ComponentProps<"div"> & { ratio: number }) {
  return (
    <div
      data-slot="aspect-ratio"
      style={{
        aspectRatio: ratio,
        ...style,
      }}
      className={cn("relative w-full", className)}
      {...props}
    />
  )
}

export { AspectRatio }
