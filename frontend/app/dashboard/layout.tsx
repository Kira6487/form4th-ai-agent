import { DashboardShell } from "../../components/dashboard-shell";
import { WorkspaceProvider } from "../../components/workspace-provider";

export default function DashboardLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <WorkspaceProvider><DashboardShell>{children}</DashboardShell></WorkspaceProvider>;
}
