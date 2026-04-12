import { Toaster as Sonner } from "sonner"

type ToasterProps = React.ComponentProps<typeof Sonner>

const Toaster = ({ ...props }: ToasterProps) => {
  return (
    <Sonner
      theme="system"
      position="top-right"
      closeButton
      richColors
      expand={false}
      visibleToasts={5}
      toastOptions={{
        classNames: {
          toast:
            "group toast rounded-[var(--radius-xl)] border border-[var(--border-primary)] bg-[var(--bg-elevated)] text-[var(--text-primary)] shadow-[var(--shadow-lg)] backdrop-blur-md",
          title: "text-[var(--text-primary)] font-medium",
          description: "text-[var(--text-secondary)]",
          success:
            "border-[var(--accent-success)] bg-[var(--bg-elevated)]",
          error:
            "border-[var(--accent-destructive)] bg-[var(--bg-elevated)]",
          warning:
            "border-[var(--accent-warning)] bg-[var(--bg-elevated)]",
          info:
            "border-[var(--accent-info)] bg-[var(--bg-elevated)]",
          actionButton:
            "bg-[var(--accent-primary)] text-[var(--text-inverse)] hover:bg-[var(--accent-primary-hover)] transition-colors duration-[var(--transition-base)]",
          cancelButton:
            "bg-[var(--bg-tertiary)] text-[var(--text-secondary)] hover:bg-[var(--bg-secondary)] transition-colors duration-[var(--transition-base)]",
          closeButton:
            "text-[var(--text-tertiary)] hover:text-[var(--text-primary)] transition-colors duration-[var(--transition-base)]",
        },
      }}
      {...props}
    />
  )
}

export { Toaster }
