import { Link } from "react-router-dom";
import { EmptyState, Page } from "../components/ui";

export default function ComingSoon({ title }: { title: string }) {
  return <Page><EmptyState title={`${title} is coming soon`} text="This part of Sentinel is built in a later phase."><Link className="btn primary" to="/dashboard">Back to dashboard</Link></EmptyState></Page>;
}
