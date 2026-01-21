import { useState } from "react"
import { useParams, Link } from "react-router-dom"
import { useMicroFrontendNavigation } from "@/hooks/useNavigation"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { StatusBadge } from "@/components/StatusBadge"
import { Spinner } from "@/components/ui/spinner"
import { EmptyState } from "@/components/EmptyState"
import { useConfirm } from "@/components/ui/confirm-dialog"
import { useToast } from "@/contexts/ToastContext"
import {
  getJob,
  getJobRuns,
  runJob,
  deleteJob,
  updateJob,
  getExportDownloadUrl,
} from "@/api/client"
import {
  ArrowLeft,
  Play,
  Trash2,
  Download,
  Upload,
  Clock,
  FileDown,
  RefreshCw,
  Pencil,
  Copy,
  AlertCircle,
} from "lucide-react"
import type { JobRun, JobDefinitionUpdate } from "@/types"

export function JobDetail() {
  const { jobId } = useParams<{ jobId: string }>()
  const { navigateTo, navigateToJobs, navigateBack } = useMicroFrontendNavigation()
  const queryClient = useQueryClient()
  const toast = useToast()
  const { confirm, ConfirmDialog } = useConfirm()

  // Edit dialog state
  const [editDialogOpen, setEditDialogOpen] = useState(false)
  const [editName, setEditName] = useState("")
  const [editCronSchedule, setEditCronSchedule] = useState("")
  const [editEnabled, setEditEnabled] = useState(true)

  // Error details dialog state
  const [errorDetailsRun, setErrorDetailsRun] = useState<JobRun | null>(null)

  const { data: job, isLoading: jobLoading } = useQuery({
    queryKey: ["job", jobId],
    queryFn: () => getJob(jobId!),
    enabled: !!jobId,
  })

  const { data: runs, isLoading: runsLoading } = useQuery({
    queryKey: ["jobRuns", jobId],
    queryFn: () => getJobRuns(jobId!),
    enabled: !!jobId,
    refetchInterval: 5000, // Poll every 5 seconds
  })

  const runMutation = useMutation({
    mutationFn: runJob,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["jobRuns", jobId] })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: deleteJob,
    onSuccess: () => {
      navigateToJobs()
    },
  })

  const updateMutation = useMutation({
    mutationFn: (data: JobDefinitionUpdate) => updateJob(jobId!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["job", jobId] })
      queryClient.invalidateQueries({ queryKey: ["jobs"] })
      setEditDialogOpen(false)
    },
  })

  const handleRun = () => {
    if (!jobId || !job) return

    if (job.job_type === "import") {
      // Navigate to import workflow with this job's entity pre-selected
      navigateTo(`/imports/new?run=${jobId}`)
      return
    }

    runMutation.mutate(jobId)
  }

  const handleDelete = async () => {
    if (!jobId) return
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

  const handleDownload = async (runId: string) => {
    try {
      const result = await getExportDownloadUrl(runId)
      if (result.download_url) {
        // Handle relative URLs (for local development) by prepending the API base
        let url = result.download_url
        if (url.startsWith("/")) {
          url = `/api${url}`
        }
        window.open(url, "_blank")
      } else {
        toast.warning("Download not available", "The export file may not have been uploaded to cloud storage.")
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown error"
      toast.error("Failed to get download URL", message)
      console.error("Failed to get download URL:", error)
    }
  }

  const openEditDialog = () => {
    if (!job) return
    setEditName(job.name)
    setEditCronSchedule(job.cron_schedule || "")
    setEditEnabled(job.enabled)
    setEditDialogOpen(true)
  }

  const handleEdit = () => {
    if (!job) return
    const updates: JobDefinitionUpdate = {}
    if (editName !== job.name) updates.name = editName
    if (editCronSchedule !== (job.cron_schedule || "")) {
      updates.cron_schedule = editCronSchedule || null
    }
    if (editEnabled !== job.enabled) updates.enabled = editEnabled

    if (Object.keys(updates).length === 0) {
      setEditDialogOpen(false)
      return
    }
    updateMutation.mutate(updates)
  }

  const handleClone = () => {
    if (!job) return
    // Navigate to the appropriate create page with clone parameter
    if (job.job_type === "export") {
      navigateTo(`/exports/new?clone=${job.id}`)
    } else {
      navigateTo(`/imports/new?clone=${job.id}`)
    }
  }

  if (jobLoading) {
    return (
      <div className="flex justify-center py-12">
        <Spinner size="lg" />
      </div>
    )
  }

  if (!job) {
    return (
      <EmptyState
        title="Job not found"
        description="The job you're looking for doesn't exist."
        action={
          <Button asChild>
            <Link to="..">Back to Jobs</Link>
          </Button>
        }
      />
    )
  }

  const isExport = job.job_type === "export"
  const config = isExport ? job.export_config : job.import_config

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={navigateBack}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-3xl font-bold tracking-tight">{job.name}</h1>
              <Badge variant={isExport ? "default" : "secondary"}>
                <span className="flex items-center gap-1">
                  {isExport ? (
                    <Download className="h-3 w-3" />
                  ) : (
                    <Upload className="h-3 w-3" />
                  )}
                  {job.job_type}
                </span>
              </Badge>
            </div>
            <p className="text-muted-foreground">
              {isExport ? "Export" : "Import"} job for {config?.entity}
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button
            onClick={handleRun}
            disabled={runMutation.isPending}
          >
            {runMutation.isPending ? (
              <Spinner size="sm" className="mr-2" />
            ) : (
              <Play className="mr-2 h-4 w-4" />
            )}
            Run Now
          </Button>
          <Button variant="outline" onClick={openEditDialog}>
            <Pencil className="mr-2 h-4 w-4" />
            Edit
          </Button>
          <Button variant="outline" onClick={handleClone}>
            <Copy className="mr-2 h-4 w-4" />
            Clone
          </Button>
          <Button
            variant="destructive"
            onClick={handleDelete}
            disabled={deleteMutation.isPending}
          >
            <Trash2 className="mr-2 h-4 w-4" />
            Delete
          </Button>
        </div>
      </div>

      {/* Job Configuration */}
      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Configuration</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-3 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Entity:</span>
                <span className="capitalize">{config?.entity}</span>
              </div>
              {isExport && job.export_config && (
                <>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Fields:</span>
                    <span>{job.export_config.fields?.length || 0} selected</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Filters:</span>
                    <span>{job.export_config.filters?.filters?.length || 0} applied</span>
                  </div>
                </>
              )}
              <div className="flex justify-between">
                <span className="text-muted-foreground">Enabled:</span>
                <Badge variant={job.enabled ? "default" : "secondary"}>
                  {job.enabled ? "Yes" : "No"}
                </Badge>
              </div>
            </div>

            {isExport && job.export_config?.fields && (
              <div className="space-y-2">
                <span className="text-sm font-medium">Fields:</span>
                <div className="flex flex-wrap gap-1">
                  {job.export_config.fields.map((f) => (
                    <Badge key={f.field} variant="outline" className="text-xs">
                      {f.as || f.field}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            {isExport && job.export_config?.filters?.filters && job.export_config.filters.filters.length > 0 && (
              <div className="space-y-2">
                <span className="text-sm font-medium">Filters:</span>
                <div className="space-y-1">
                  {job.export_config.filters.filters.map((filter, index) => (
                    <div key={index} className="flex items-center gap-2 text-sm">
                      <Badge variant="secondary" className="text-xs font-normal">
                        {filter.field}
                      </Badge>
                      <span className="text-muted-foreground">{filter.operator}</span>
                      <code className="rounded bg-muted px-1.5 py-0.5 text-xs">
                        {String(filter.value)}
                      </code>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Schedule</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-3 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Type:</span>
                <span>{job.cron_schedule ? "Scheduled" : "Manual"}</span>
              </div>
              {job.cron_schedule && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Cron:</span>
                  <code className="rounded bg-muted px-1.5 py-0.5 text-xs">
                    {job.cron_schedule}
                  </code>
                </div>
              )}
              <div className="flex justify-between">
                <span className="text-muted-foreground">Created:</span>
                <span>{new Date(job.created_at).toLocaleDateString()}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Last Updated:</span>
                <span>{new Date(job.updated_at).toLocaleDateString()}</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Job Runs */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Run History</CardTitle>
              <CardDescription>
                Previous executions of this job
              </CardDescription>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() =>
                queryClient.invalidateQueries({ queryKey: ["jobRuns", jobId] })
              }
            >
              <RefreshCw className="mr-2 h-4 w-4" />
              Refresh
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {runsLoading ? (
            <div className="flex justify-center py-8">
              <Spinner />
            </div>
          ) : !runs || runs.length === 0 ? (
            <EmptyState
              icon={<Clock className="h-6 w-6" />}
              title="No runs yet"
              description="This job hasn't been executed yet."
              action={
                <Button onClick={handleRun} disabled={runMutation.isPending}>
                  <Play className="mr-2 h-4 w-4" />
                  Run Now
                </Button>
              }
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Run ID</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Started</TableHead>
                  <TableHead>Completed</TableHead>
                  <TableHead>Duration</TableHead>
                  {!isExport && <TableHead>Result</TableHead>}
                  <TableHead>Error</TableHead>
                  {isExport && <TableHead>Download</TableHead>}
                </TableRow>
              </TableHeader>
              <TableBody>
                {runs.map((run: JobRun) => {
                  const started = run.started_at
                    ? new Date(run.started_at)
                    : null
                  const completed = run.completed_at
                    ? new Date(run.completed_at)
                    : null
                  const duration =
                    started && completed
                      ? Math.round(
                          (completed.getTime() - started.getTime()) / 1000
                        )
                      : null

                  return (
                    <TableRow key={run.id}>
                      <TableCell>
                        <code className="rounded bg-muted px-1.5 py-0.5 text-xs">
                          {run.id.slice(0, 8)}...
                        </code>
                      </TableCell>
                      <TableCell>
                        <StatusBadge status={run.status} />
                      </TableCell>
                      <TableCell>
                        {started ? started.toLocaleString() : "-"}
                      </TableCell>
                      <TableCell>
                        {completed ? completed.toLocaleString() : "-"}
                      </TableCell>
                      <TableCell>
                        {duration !== null ? `${duration}s` : "-"}
                      </TableCell>
                      {!isExport && (
                        <TableCell>
                          {run.result_metadata && (run.status === "succeeded" || run.status === "failed") ? (() => {
                            const meta = run.result_metadata as Record<string, number>
                            const imported = meta.imported_count || 0
                            const updated = meta.updated_count || 0
                            const deleted = meta.deleted_count || 0
                            const skipped = meta.skipped_count || 0
                            return (
                              <div className="flex items-center gap-2 text-xs">
                                {imported > 0 && (
                                  <span className="text-green-600">+{imported} created</span>
                                )}
                                {updated > 0 && (
                                  <span className="text-blue-600">{updated} updated</span>
                                )}
                                {deleted > 0 && (
                                  <span className="text-orange-600">{deleted} deleted</span>
                                )}
                                {skipped > 0 && (
                                  <span className="text-muted-foreground">{skipped} skipped</span>
                                )}
                                {!imported && !updated && !deleted && !skipped && (
                                  <span className="text-muted-foreground">No changes</span>
                                )}
                              </div>
                            )
                          })() : (
                            "-"
                          )}
                        </TableCell>
                      )}
                      <TableCell>
                        {run.status === "failed" && run.error_message ? (
                          <div className="flex items-center gap-2">
                            <span
                              className="text-xs text-destructive max-w-[180px] block truncate cursor-help"
                              title={run.error_message}
                            >
                              {run.error_message}
                            </span>
                            {run.result_metadata &&
                              Array.isArray(
                                (run.result_metadata as Record<string, unknown>)
                                  .import_errors
                              ) &&
                              ((run.result_metadata as Record<string, unknown>)
                                .import_errors as unknown[]).length > 0 && (
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  className="h-6 px-2 text-xs"
                                  onClick={() => setErrorDetailsRun(run)}
                                >
                                  <AlertCircle className="mr-1 h-3 w-3" />
                                  Details
                                </Button>
                              )}
                          </div>
                        ) : (
                          "-"
                        )}
                      </TableCell>
                      {isExport && (
                        <TableCell>
                          {run.status === "succeeded" && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleDownload(run.id)}
                            >
                              <FileDown className="mr-2 h-4 w-4" />
                              Download
                            </Button>
                          )}
                        </TableCell>
                      )}
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Edit Dialog */}
      <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Job</DialogTitle>
            <DialogDescription>
              Update job name, schedule, and enabled status. To modify the export/import
              configuration, use Clone to create a new job with different settings.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="edit-name">Name</Label>
              <Input
                id="edit-name"
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                placeholder="Job name"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit-schedule">Cron Schedule (optional)</Label>
              <Input
                id="edit-schedule"
                value={editCronSchedule}
                onChange={(e) => setEditCronSchedule(e.target.value)}
                placeholder="e.g., 0 9 * * * (daily at 9am)"
              />
              <p className="text-xs text-muted-foreground">
                Leave empty for manual execution only
              </p>
            </div>
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label htmlFor="edit-enabled">Enabled</Label>
                <p className="text-xs text-muted-foreground">
                  Disabled jobs won't run on schedule
                </p>
              </div>
              <Switch
                id="edit-enabled"
                checked={editEnabled}
                onCheckedChange={setEditEnabled}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleEdit}
              disabled={updateMutation.isPending || !editName.trim()}
            >
              {updateMutation.isPending ? (
                <Spinner size="sm" className="mr-2" />
              ) : null}
              Save Changes
            </Button>
          </DialogFooter>
          {updateMutation.isError && (
            <p className="text-sm text-destructive mt-2">
              Failed to update job: {updateMutation.error instanceof Error ? updateMutation.error.message : "Unknown error"}
            </p>
          )}
        </DialogContent>
      </Dialog>

      {/* Import Error Details Dialog */}
      <Dialog
        open={!!errorDetailsRun}
        onOpenChange={(open) => !open && setErrorDetailsRun(null)}
      >
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-hidden flex flex-col">
          <DialogHeader>
            <DialogTitle>Import Error Details</DialogTitle>
            <DialogDescription>
              {errorDetailsRun?.error_message}
            </DialogDescription>
          </DialogHeader>
          <div className="flex-1 overflow-auto">
            {errorDetailsRun?.result_metadata && (
              <div className="space-y-4">
                {/* Summary */}
                <div className="grid grid-cols-3 gap-4 text-sm">
                  <div className="rounded-lg border p-3">
                    <p className="text-muted-foreground">Imported</p>
                    <p className="text-xl font-semibold text-green-600">
                      {(errorDetailsRun.result_metadata as Record<string, unknown>)
                        .imported_count as number ?? 0}
                    </p>
                  </div>
                  <div className="rounded-lg border p-3">
                    <p className="text-muted-foreground">Updated</p>
                    <p className="text-xl font-semibold text-blue-600">
                      {(errorDetailsRun.result_metadata as Record<string, unknown>)
                        .updated_count as number ?? 0}
                    </p>
                  </div>
                  <div className="rounded-lg border p-3">
                    <p className="text-muted-foreground">Failed</p>
                    <p className="text-xl font-semibold text-red-600">
                      {(errorDetailsRun.result_metadata as Record<string, unknown>)
                        .failed_count as number ?? 0}
                    </p>
                  </div>
                </div>

                {/* Error list */}
                {Array.isArray(
                  (errorDetailsRun.result_metadata as Record<string, unknown>)
                    .import_errors
                ) && (
                  <div className="space-y-2">
                    <h4 className="font-medium">Failed Records</h4>
                    <div className="rounded-lg border">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead className="w-[80px]">Row</TableHead>
                            <TableHead>Error</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {(
                            (
                              errorDetailsRun.result_metadata as Record<
                                string,
                                unknown
                              >
                            ).import_errors as Array<{
                              row?: number
                              message: string
                            }>
                          ).map((error, index) => (
                            <TableRow key={index}>
                              <TableCell className="font-mono text-xs">
                                {error.row ?? "-"}
                              </TableCell>
                              <TableCell className="text-sm text-destructive">
                                {error.message}
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setErrorDetailsRun(null)}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {ConfirmDialog}
      </div>
  )
}
