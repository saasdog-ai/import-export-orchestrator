import { useQuery } from "@tanstack/react-query"
import { Link } from "react-router-dom"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { StatusBadge } from "@/components/StatusBadge"
import { Spinner } from "@/components/ui/spinner"
import { EmptyState } from "@/components/EmptyState"
import { getJobs, checkHealth } from "@/api/client"
import {
  Download,
  Upload,
  Briefcase,
  ArrowRight,
  CheckCircle,
  AlertCircle,
} from "lucide-react"
import type { JobDefinition } from "@/types"

export function Dashboard() {
  const { data: health, isLoading: healthLoading } = useQuery({
    queryKey: ["health"],
    queryFn: checkHealth,
    refetchInterval: 30000,
  })

  // Fetch recent jobs (first page, 5 items)
  const { data: jobsData, isLoading: jobsLoading } = useQuery({
    queryKey: ["jobs", { page: 1, page_size: 5 }],
    queryFn: () => getJobs({ page: 1, page_size: 5 }),
  })

  // Fetch export count
  const { data: exportData } = useQuery({
    queryKey: ["jobs", { job_type: "export", page: 1, page_size: 1 }],
    queryFn: () => getJobs({ job_type: "export", page: 1, page_size: 1 }),
  })

  // Fetch import count
  const { data: importData } = useQuery({
    queryKey: ["jobs", { job_type: "import", page: 1, page_size: 1 }],
    queryFn: () => getJobs({ job_type: "import", page: 1, page_size: 1 }),
  })

  const recentJobs = jobsData?.items || []
  const totalJobs = jobsData?.total || 0
  const exportCount = exportData?.total || 0
  const importCount = importData?.total || 0

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground">
          Manage your data imports and exports
        </p>
      </div>

      {/* Quick actions */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <Download className="h-4 w-4" />
              Export Data
            </CardTitle>
            <CardDescription>
              Export your data to CSV or Excel format
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild className="w-full">
              <Link to="/exports/new">
                Create Export
                <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <Upload className="h-4 w-4" />
              Import Data
            </CardTitle>
            <CardDescription>
              Import data from CSV or Excel files
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild className="w-full">
              <Link to="/imports/new">
                Start Import
                <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <Briefcase className="h-4 w-4" />
              Scheduled Jobs
            </CardTitle>
            <CardDescription>
              View and manage automated jobs
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild variant="outline" className="w-full">
              <Link to="/jobs">
                View Jobs
                <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>System Status</CardDescription>
          </CardHeader>
          <CardContent>
            {healthLoading ? (
              <Spinner size="sm" />
            ) : health?.status === "healthy" ? (
              <div className="flex items-center gap-2 text-green-600">
                <CheckCircle className="h-5 w-5" />
                <span className="text-2xl font-bold">Online</span>
              </div>
            ) : (
              <div className="flex items-center gap-2 text-red-600">
                <AlertCircle className="h-5 w-5" />
                <span className="text-2xl font-bold">Offline</span>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Total Jobs</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {jobsLoading ? <Spinner size="sm" /> : totalJobs}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Export Jobs</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {jobsLoading ? <Spinner size="sm" /> : exportCount}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Import Jobs</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {jobsLoading ? <Spinner size="sm" /> : importCount}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Recent Jobs */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Recent Jobs</CardTitle>
              <CardDescription>
                Your most recently created job definitions
              </CardDescription>
            </div>
            <Button asChild variant="outline" size="sm">
              <Link to="/jobs">View all</Link>
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {jobsLoading ? (
            <div className="flex justify-center py-8">
              <Spinner />
            </div>
          ) : recentJobs.length === 0 ? (
            <EmptyState
              icon={<Briefcase className="h-6 w-6" />}
              title="No jobs yet"
              description="Create your first export or import job to get started."
              action={
                <div className="flex gap-2">
                  <Button asChild size="sm">
                    <Link to="/exports/new">Create Export</Link>
                  </Button>
                  <Button asChild variant="outline" size="sm">
                    <Link to="/imports/new">Start Import</Link>
                  </Button>
                </div>
              }
            />
          ) : (
            <div className="space-y-4">
              {recentJobs.map((job: JobDefinition) => (
                <Link
                  key={job.id}
                  to={`/jobs/${job.id}`}
                  className="flex items-center justify-between rounded-lg border p-4 transition-colors hover:bg-muted/50"
                >
                  <div className="flex items-center gap-4">
                    <div
                      className={`flex h-10 w-10 items-center justify-center rounded-lg ${
                        job.job_type === "export"
                          ? "bg-blue-100 text-blue-600"
                          : "bg-green-100 text-green-600"
                      }`}
                    >
                      {job.job_type === "export" ? (
                        <Download className="h-5 w-5" />
                      ) : (
                        <Upload className="h-5 w-5" />
                      )}
                    </div>
                    <div>
                      <p className="font-medium">{job.name}</p>
                      <p className="text-sm text-muted-foreground">
                        {job.job_type === "export"
                          ? job.export_config?.entity
                          : job.import_config?.entity}{" "}
                        &middot; {job.job_type}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    {job.last_run ? (
                      <StatusBadge status={job.last_run.status} />
                    ) : (
                      <span className="text-muted-foreground text-sm">No runs</span>
                    )}
                    <ArrowRight className="h-4 w-4 text-muted-foreground" />
                  </div>
                </Link>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
