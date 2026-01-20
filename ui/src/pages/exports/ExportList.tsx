import { useState } from "react"
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
import { getJobs } from "@/api/client"
import { Download, Plus, ArrowRight, ChevronLeft, ChevronRight } from "lucide-react"
import type { JobsQueryParams } from "@/types"
import { ENTITIES } from "@/constants"

export function ExportList() {
  const [page, setPage] = useState(1)
  const [pageSize] = useState(20)
  const [entityFilter, setEntityFilter] = useState<string>("")

  const queryParams: JobsQueryParams = {
    page,
    page_size: pageSize,
    job_type: "export",
    ...(entityFilter && { entity: entityFilter }),
  }

  const { data, isLoading, isFetching } = useQuery({
    queryKey: ["jobs", queryParams],
    queryFn: () => getJobs(queryParams),
  })

  const exportJobs = data?.items || []
  const totalPages = data?.total_pages || 1
  const total = data?.total || 0

  const handleFilterChange = (value: string) => {
    setPage(1)
    setEntityFilter(value)
  }

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Exports</h1>
          <p className="text-muted-foreground">
            Export your data to CSV or Excel format
          </p>
        </div>
        <Button asChild>
          <Link to="/exports/new">
            <Plus className="mr-2 h-4 w-4" />
            New Export
          </Link>
        </Button>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Export Jobs</CardTitle>
              <CardDescription>
                {total > 0
                  ? `${total} export job${total !== 1 ? "s" : ""} found`
                  : "Saved export configurations that can be run on demand or scheduled"
                }
              </CardDescription>
            </div>
            <select
              className="rounded-md border border-input bg-background px-3 py-2 text-sm"
              value={entityFilter}
              onChange={(e) => handleFilterChange(e.target.value)}
            >
              <option value="">All Entities</option>
              {ENTITIES.map((entity) => (
                <option key={entity} value={entity}>
                  {entity.charAt(0).toUpperCase() + entity.slice(1)}
                </option>
              ))}
            </select>
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex justify-center py-8">
              <Spinner />
            </div>
          ) : exportJobs.length === 0 ? (
            <EmptyState
              icon={<Download className="h-6 w-6" />}
              title="No export jobs"
              description={
                entityFilter
                  ? "No export jobs match the current filter. Try a different entity."
                  : "Create your first export to start extracting data."
              }
              action={
                entityFilter ? (
                  <Button variant="outline" onClick={() => setEntityFilter("")}>
                    Clear Filter
                  </Button>
                ) : (
                  <Button asChild>
                    <Link to="/exports/new">
                      <Plus className="mr-2 h-4 w-4" />
                      Create Export
                    </Link>
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
                    <TableHead>Entity</TableHead>
                    <TableHead>Schedule</TableHead>
                    <TableHead className="w-[100px]">Status</TableHead>
                    <TableHead>Last Run</TableHead>
                    <TableHead className="w-[50px]"></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {exportJobs.map((job) => (
                    <TableRow key={job.id}>
                      <TableCell className="font-medium">{job.name}</TableCell>
                      <TableCell className="capitalize">
                        {job.export_config?.entity}
                      </TableCell>
                      <TableCell>
                        {job.cron_schedule || "Manual"}
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
                        <Button asChild variant="ghost" size="icon">
                          <Link to={`/jobs/${job.id}`}>
                            <ArrowRight className="h-4 w-4" />
                          </Link>
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between border-t pt-4 mt-4">
                  <div className="text-sm text-muted-foreground">
                    Page {page} of {totalPages} ({total} total exports)
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
    </div>
  )
}
