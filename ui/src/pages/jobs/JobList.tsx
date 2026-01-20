import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Link } from "react-router-dom"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { StatusBadge } from "@/components/StatusBadge"
import { Spinner } from "@/components/ui/spinner"
import { EmptyState } from "@/components/EmptyState"
import { useConfirm } from "@/components/ui/confirm-dialog"
import { useToast } from "@/contexts/ToastContext"
import { getJobs, runJob, deleteJob } from "@/api/client"
import {
  Briefcase,
  Plus,
  ArrowRight,
  Play,
  Trash2,
  Download,
  Upload,
  ChevronLeft,
  ChevronRight,
  X,
} from "lucide-react"
import type { JobDefinition, JobsQueryParams } from "@/types"
import { ENTITIES } from "@/constants"

export function JobList() {
  const queryClient = useQueryClient()
  const toast = useToast()
  const { confirm, ConfirmDialog } = useConfirm()
  const [page, setPage] = useState(1)
  const [pageSize] = useState(20)
  const [jobTypeFilter, setJobTypeFilter] = useState<"export" | "import" | "">("")
  const [entityFilter, setEntityFilter] = useState<string>("")
  const [startDate, setStartDate] = useState<string>("")
  const [endDate, setEndDate] = useState<string>("")

  const queryParams: JobsQueryParams = {
    page,
    page_size: pageSize,
    ...(jobTypeFilter && { job_type: jobTypeFilter as "export" | "import" }),
    ...(entityFilter && { entity: entityFilter }),
    ...(startDate && { start_date: startDate }),
    ...(endDate && { end_date: endDate }),
  }

  const { data, isLoading, isFetching } = useQuery({
    queryKey: ["jobs", queryParams],
    queryFn: () => getJobs(queryParams),
  })

  const jobs = data?.items || []
  const totalPages = data?.total_pages || 1
  const total = data?.total || 0

  const runMutation = useMutation({
    mutationFn: runJob,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["jobs"] })
      toast.success("Job started successfully", `Run ID: ${data.id}`)
    },
    onError: (error) => {
      toast.error("Failed to run job", error instanceof Error ? error.message : "Unknown error")
    },
  })

  const deleteMutation = useMutation({
    mutationFn: deleteJob,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["jobs"] })
    },
  })

  const handleRun = (jobId: string, jobType: string, jobName: string) => {
    if (jobType === "import") {
      toast.info(
        "Import requires file upload",
        `To run "${jobName}", go to Imports → New Import and upload your CSV file.`
      )
      return
    }
    runMutation.mutate(jobId)
  }

  const handleDelete = async (jobId: string) => {
    const confirmed = await confirm({
      title: "Delete Job",
      description: "Are you sure you want to delete this job? This action cannot be undone.",
      confirmLabel: "Delete",
      variant: "destructive",
    })
    if (confirmed) {
      deleteMutation.mutate(jobId)
    }
  }

  const handleFilterChange = (type: "jobType" | "entity" | "startDate" | "endDate", value: string) => {
    setPage(1) // Reset to first page when filter changes
    if (type === "jobType") {
      setJobTypeFilter(value as "export" | "import" | "")
    } else if (type === "entity") {
      setEntityFilter(value)
    } else if (type === "startDate") {
      setStartDate(value)
    } else if (type === "endDate") {
      setEndDate(value)
    }
  }

  const clearAllFilters = () => {
    setPage(1)
    setJobTypeFilter("")
    setEntityFilter("")
    setStartDate("")
    setEndDate("")
  }

  const hasFilters = jobTypeFilter || entityFilter || startDate || endDate

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Jobs</h1>
          <p className="text-muted-foreground">
            Manage your import and export job definitions
          </p>
        </div>
        <div className="flex gap-2">
          <Button asChild variant="outline">
            <Link to="/exports/new">
              <Download className="mr-2 h-4 w-4" />
              New Export
            </Link>
          </Button>
          <Button asChild>
            <Link to="/imports/new">
              <Upload className="mr-2 h-4 w-4" />
              New Import
            </Link>
          </Button>
        </div>
      </div>

      <Card>
        <CardHeader>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>All Jobs</CardTitle>
                <CardDescription>
                  {total > 0 ? `${total} job${total !== 1 ? "s" : ""} found` : "View and manage all your job definitions"}
                </CardDescription>
              </div>
              {hasFilters && (
                <Button variant="ghost" size="sm" onClick={clearAllFilters}>
                  <X className="mr-1 h-3 w-3" />
                  Clear Filters
                </Button>
              )}
            </div>
            <div className="flex flex-wrap items-end gap-4">
              <div className="space-y-1">
                <Label className="text-xs text-muted-foreground">Type</Label>
                <select
                  className="rounded-md border border-input bg-background px-3 py-2 text-sm h-9"
                  value={jobTypeFilter}
                  onChange={(e) => handleFilterChange("jobType", e.target.value)}
                >
                  <option value="">All Types</option>
                  <option value="export">Export</option>
                  <option value="import">Import</option>
                </select>
              </div>
              <div className="space-y-1">
                <Label className="text-xs text-muted-foreground">Entity</Label>
                <select
                  className="rounded-md border border-input bg-background px-3 py-2 text-sm h-9"
                  value={entityFilter}
                  onChange={(e) => handleFilterChange("entity", e.target.value)}
                >
                  <option value="">All Entities</option>
                  {ENTITIES.map((entity) => (
                    <option key={entity} value={entity}>
                      {entity.charAt(0).toUpperCase() + entity.slice(1)}
                    </option>
                  ))}
                </select>
              </div>
              <div className="space-y-1">
                <Label className="text-xs text-muted-foreground">Created From</Label>
                <Input
                  type="date"
                  className="h-9 w-[150px]"
                  value={startDate}
                  onChange={(e) => handleFilterChange("startDate", e.target.value)}
                />
              </div>
              <div className="space-y-1">
                <Label className="text-xs text-muted-foreground">Created To</Label>
                <Input
                  type="date"
                  className="h-9 w-[150px]"
                  value={endDate}
                  onChange={(e) => handleFilterChange("endDate", e.target.value)}
                />
              </div>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex justify-center py-8">
              <Spinner />
            </div>
          ) : jobs.length === 0 ? (
            <EmptyState
              icon={<Briefcase className="h-6 w-6" />}
              title="No jobs found"
              description={
                hasFilters
                  ? "No jobs match the current filters. Try adjusting your filters."
                  : "Create your first export or import job to get started."
              }
              action={
                !hasFilters ? (
                  <div className="flex gap-2">
                    <Button asChild>
                      <Link to="/exports/new">
                        <Plus className="mr-2 h-4 w-4" />
                        Create Export
                      </Link>
                    </Button>
                    <Button asChild variant="outline">
                      <Link to="/imports/new">
                        <Plus className="mr-2 h-4 w-4" />
                        Start Import
                      </Link>
                    </Button>
                  </div>
                ) : (
                  <Button variant="outline" onClick={clearAllFilters}>
                    Clear Filters
                  </Button>
                )
              }
            />
          ) : (
            <>
              {isFetching && !isLoading && (
                <div className="absolute top-2 right-2">
                  <Spinner size="sm" />
                </div>
              )}
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Entity</TableHead>
                    <TableHead>Schedule</TableHead>
                    <TableHead className="w-[100px]">Status</TableHead>
                    <TableHead>Last Run</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {jobs.map((job: JobDefinition) => (
                    <TableRow key={job.id}>
                      <TableCell>
                        <Link
                          to={`/jobs/${job.id}`}
                          className="font-medium hover:underline"
                        >
                          {job.name}
                        </Link>
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant={
                            job.job_type === "export" ? "default" : "secondary"
                          }
                        >
                          <span className="flex items-center gap-1">
                            {job.job_type === "export" ? (
                              <Download className="h-3 w-3" />
                            ) : (
                              <Upload className="h-3 w-3" />
                            )}
                            {job.job_type}
                          </span>
                        </Badge>
                      </TableCell>
                      <TableCell className="capitalize">
                        {job.job_type === "export"
                          ? job.export_config?.entity
                          : job.import_config?.entity}
                      </TableCell>
                      <TableCell>
                        {job.cron_schedule ? (
                          <code className="rounded bg-muted px-1.5 py-0.5 text-xs">
                            {job.cron_schedule}
                          </code>
                        ) : (
                          <span className="text-muted-foreground">Manual</span>
                        )}
                      </TableCell>
                      <TableCell>
                        {job.last_run ? (
                          <StatusBadge status={job.last_run.status} />
                        ) : (
                          <span className="text-muted-foreground text-sm">-</span>
                        )}
                      </TableCell>
                      <TableCell>
                        {job.last_run?.completed_at ? (
                          <span className="text-sm">
                            {new Date(job.last_run.completed_at).toLocaleString()}
                          </span>
                        ) : job.last_run?.started_at ? (
                          <span className="text-sm text-muted-foreground">
                            Started {new Date(job.last_run.started_at).toLocaleString()}
                          </span>
                        ) : (
                          <span className="text-muted-foreground text-sm">Never</span>
                        )}
                      </TableCell>
                      <TableCell>
                        <div className="flex justify-end gap-2">
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleRun(job.id, job.job_type, job.name)}
                            disabled={runMutation.isPending}
                            title={job.job_type === "import" ? "Import requires file upload" : "Run job"}
                          >
                            <Play className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleDelete(job.id)}
                            disabled={deleteMutation.isPending}
                            title="Delete job"
                          >
                            <Trash2 className="h-4 w-4 text-destructive" />
                          </Button>
                          <Button asChild variant="ghost" size="icon">
                            <Link to={`/jobs/${job.id}`}>
                              <ArrowRight className="h-4 w-4" />
                            </Link>
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between border-t pt-4 mt-4">
                  <div className="text-sm text-muted-foreground">
                    Page {page} of {totalPages} ({total} total jobs)
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage((p) => Math.max(1, p - 1))}
                      disabled={page === 1 || isFetching}
                    >
                      <ChevronLeft className="h-4 w-4 mr-1" />
                      Previous
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                      disabled={page === totalPages || isFetching}
                    >
                      Next
                      <ChevronRight className="h-4 w-4 ml-1" />
                    </Button>
                  </div>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>
      {ConfirmDialog}
    </div>
  )
}
