import { useState, useEffect } from "react"
import { useNavigate, useSearchParams } from "react-router-dom"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select } from "@/components/ui/select"
import { Badge } from "@/components/ui/badge"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog"
import { Spinner } from "@/components/ui/spinner"
import { useSchema } from "@/hooks/useSchema"
import { createJob, createExport, previewExport, getJob } from "@/api/client"
import type {
  ExportEntity,
  ExportField,
  ExportFilterGroup,
  SchemaField,
  SchemaRelationship,
} from "@/types"
import {
  ArrowLeft,
  Download,
  Save,
  Eye,
  ChevronDown,
  ChevronUp,
  Plus,
  X,
  Filter,
} from "lucide-react"
import { getClientId } from "@/lib/auth"
import { useToast } from "@/contexts/ToastContext"

// Relative date options for filters
const RELATIVE_DATE_OPTIONS = [
  { value: "relative:last_7_days", label: "Last 7 days" },
  { value: "relative:last_30_days", label: "Last 30 days" },
  { value: "relative:last_90_days", label: "Last 90 days" },
  { value: "relative:this_month", label: "This month" },
  { value: "relative:last_month", label: "Last month" },
  { value: "relative:this_quarter", label: "This quarter" },
  { value: "relative:this_year", label: "This year" },
]

const FILTER_OPERATORS = [
  { value: "eq", label: "Equals" },
  { value: "ne", label: "Not equals" },
  { value: "gt", label: "Greater than" },
  { value: "gte", label: "Greater than or equal" },
  { value: "lt", label: "Less than" },
  { value: "lte", label: "Less than or equal" },
  { value: "contains", label: "Contains" },
  { value: "startswith", label: "Starts with" },
]

interface FieldConfig extends ExportField {
  id: string
  label: string
  selected: boolean
  isRelationship?: boolean
  type?: string
}

interface FilterConfig {
  id: string
  field: string
  operator: string
  value: string
  useRelativeDate: boolean
}

export function ExportCreate() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const toast = useToast()
  const [searchParams] = useSearchParams()
  const cloneJobId = searchParams.get("clone")
  const { data: schema, isLoading: schemaLoading } = useSchema()

  // Fetch job to clone if cloneJobId is present
  const { data: cloneSource, isLoading: cloneLoading } = useQuery({
    queryKey: ["job", cloneJobId],
    queryFn: () => getJob(cloneJobId!),
    enabled: !!cloneJobId,
  })

  // Form state
  const [entity, setEntity] = useState<ExportEntity | "">("")
  const [fields, setFields] = useState<FieldConfig[]>([])
  const [filters, setFilters] = useState<FilterConfig[]>([])
  const [jobName, setJobName] = useState("")
  const [cloneInitialized, setCloneInitialized] = useState(false)

  // UI state
  const [fieldsExpanded, setFieldsExpanded] = useState(false)
  const [filtersExpanded, setFiltersExpanded] = useState(false)
  const [previewOpen, setPreviewOpen] = useState(false)
  const [previewData, setPreviewData] = useState<Record<string, unknown>[]>([])

  const selectedEntity = schema?.entities.find((e) => e.name === entity)
  const selectedFieldCount = fields.filter((f) => f.selected).length
  const allFieldsSelected = fields.length > 0 && fields.every((f) => f.selected)
  const isCloning = !!cloneJobId

  // Initialize entity from clone source
  useEffect(() => {
    if (!cloneSource || !schema || cloneInitialized) return
    if (cloneSource.export_config?.entity) {
      setEntity(cloneSource.export_config.entity)
      setJobName(`${cloneSource.name} (Copy)`)
    }
  }, [cloneSource, schema, cloneInitialized])

  // Initialize fields when entity changes
  useEffect(() => {
    if (!entity || !schema) return

    const entitySchema = schema.entities.find((e) => e.name === entity)
    if (!entitySchema) return

    const fieldConfigs: FieldConfig[] = entitySchema.fields.map(
      (f: SchemaField) => ({
        id: f.name,
        field: f.name,
        as: f.label,
        label: f.label,
        selected: true,
        type: f.type,
      })
    )

    // Add relationship fields
    entitySchema.relationships?.forEach((rel: SchemaRelationship) => {
      rel.fields.forEach((f) => {
        fieldConfigs.push({
          id: `${rel.name}.${f.name}`,
          field: `${rel.name}.${f.name}`,
          as: `${rel.label} ${f.label}`,
          label: `${rel.label} ${f.label}`,
          selected: false,
          isRelationship: true,
          type: f.type,
        })
      })
    })

    // If cloning, apply the clone source configuration
    if (cloneSource?.export_config && !cloneInitialized) {
      const sourceFields = cloneSource.export_config.fields || []
      const sourceFieldMap = new Map(sourceFields.map((f) => [f.field, f]))

      // Update field configs based on clone source
      const updatedFields = fieldConfigs.map((fc) => {
        const sourceField = sourceFieldMap.get(fc.field)
        if (sourceField) {
          return {
            ...fc,
            selected: true,
            as: sourceField.as || fc.label,
          }
        }
        return { ...fc, selected: false }
      })

      setFields(updatedFields)

      // Apply filters from clone source
      if (cloneSource.export_config.filters?.filters) {
        const sourceFilters = cloneSource.export_config.filters.filters.map((f) => ({
          id: crypto.randomUUID(),
          field: f.field,
          operator: f.operator,
          value: String(f.value),
          useRelativeDate: String(f.value).startsWith("relative:"),
        }))
        setFilters(sourceFilters)
        if (sourceFilters.length > 0) {
          setFiltersExpanded(true)
        }
      }

      // Expand fields section when cloning so user can see/modify configuration
      setFieldsExpanded(true)
      setCloneInitialized(true)
    } else if (!cloneSource) {
      setFields(fieldConfigs)
      setFilters([])
    }
  }, [entity, schema, cloneSource, cloneInitialized])

  // Mutations
  const exportMutation = useMutation({
    mutationFn: createExport,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["jobs"] })
      toast.success("Export started!", `Run ID: ${data.run_id}`)
      navigate("/exports")
    },
    onError: (error) => {
      toast.error("Export failed", error.message)
    },
    retry: false,
  })

  const saveMutation = useMutation({
    mutationFn: createJob,
    onSuccess: (job) => {
      queryClient.invalidateQueries({ queryKey: ["jobs"] })
      toast.success("Job saved successfully")
      navigate(`/jobs/${job.id}`)
    },
    onError: (error) => {
      toast.error("Failed to save job", error.message)
    },
    retry: false,
  })

  const previewMutation = useMutation({
    mutationFn: previewExport,
    onSuccess: (data) => {
      setPreviewData(data.records)
      setPreviewOpen(true)
    },
  })

  // Build export request
  const buildExportRequest = () => {
    const selectedFields = fields
      .filter((f) => f.selected)
      .map((f) => ({ field: f.field, as: f.as || undefined }))

    const filterGroup: ExportFilterGroup | undefined =
      filters.length > 0
        ? {
            operator: "and",
            filters: filters.map((f) => ({
              field: f.field,
              operator: f.operator,
              value: f.useRelativeDate ? f.value : parseFilterValue(f.value),
            })),
          }
        : undefined

    return {
      entity: entity as ExportEntity,
      fields: selectedFields,
      filters: filterGroup,
    }
  }

  const parseFilterValue = (value: string): unknown => {
    // Try to parse as number
    const num = Number(value)
    if (!isNaN(num)) return num
    // Return as string
    return value
  }

  // Handlers
  const handleExportNow = () => {
    if (!entity || selectedFieldCount === 0) return
    exportMutation.mutate(buildExportRequest())
  }

  const handleSaveJob = () => {
    if (!entity || selectedFieldCount === 0 || !jobName) return
    const clientId = getClientId()
    if (!clientId) {
      toast.error("Unable to save job", "No client ID available. Please log in again.")
      return
    }
    saveMutation.mutate({
      client_id: clientId,
      name: jobName,
      job_type: "export",
      export_config: buildExportRequest(),
      enabled: true,
    })
  }

  const handlePreview = () => {
    if (!entity || selectedFieldCount === 0) return
    previewMutation.mutate({ ...buildExportRequest(), limit: 10 })
  }

  const handleFieldToggle = (id: string) => {
    setFields((prev) =>
      prev.map((f) => (f.id === id ? { ...f, selected: !f.selected } : f))
    )
  }

  const handleFieldRename = (id: string, newName: string) => {
    setFields((prev) =>
      prev.map((f) => (f.id === id ? { ...f, as: newName } : f))
    )
  }

  const handleSelectAll = () => {
    setFields((prev) => prev.map((f) => ({ ...f, selected: true })))
  }

  const handleSelectNone = () => {
    setFields((prev) => prev.map((f) => ({ ...f, selected: false })))
  }

  const addFilter = () => {
    const dateField = fields.find((f) => f.type === "date")
    setFilters((prev) => [
      ...prev,
      {
        id: crypto.randomUUID(),
        field: dateField?.field || fields[0]?.field || "",
        operator: "gte",
        value: "relative:last_30_days",
        useRelativeDate: true,
      },
    ])
    setFiltersExpanded(true)
  }

  const removeFilter = (id: string) => {
    setFilters((prev) => prev.filter((f) => f.id !== id))
  }

  const updateFilter = (id: string, updates: Partial<FilterConfig>) => {
    setFilters((prev) =>
      prev.map((f) => (f.id === id ? { ...f, ...updates } : f))
    )
  }

  if (schemaLoading || cloneLoading) {
    return (
      <div className="flex justify-center py-12">
        <Spinner size="lg" />
      </div>
    )
  }

  const canExport = entity && selectedFieldCount > 0
  const canSave = canExport && jobName.trim().length > 0

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate(-1)}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div>
          <h1 className="text-3xl font-bold tracking-tight">
            {isCloning ? "Clone Export" : "Export Data"}
          </h1>
          <p className="text-muted-foreground">
            {isCloning
              ? `Cloning from "${cloneSource?.name}" - modify fields and filters as needed`
              : "Configure and export your data"}
          </p>
        </div>
      </div>

      {/* Entity Selection */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Entity</CardTitle>
        </CardHeader>
        <CardContent>
          <Select
            value={entity}
            onChange={(e) => setEntity(e.target.value as ExportEntity)}
            className="max-w-xs"
          >
            <option value="">Select entity to export...</option>
            {schema?.entities.map((e) => (
              <option key={e.name} value={e.name}>
                {e.label}
              </option>
            ))}
          </Select>
        </CardContent>
      </Card>

      {entity && (
        <>
          {/* Fields Section */}
          <Card>
            <CardHeader
              className="pb-3 cursor-pointer"
              onClick={() => setFieldsExpanded(!fieldsExpanded)}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <CardTitle className="text-base">Fields</CardTitle>
                  <Badge variant="secondary">
                    {selectedFieldCount} of {fields.length} selected
                  </Badge>
                </div>
                <div className="flex items-center gap-2">
                  {!fieldsExpanded && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation()
                        allFieldsSelected ? handleSelectNone() : handleSelectAll()
                      }}
                    >
                      {allFieldsSelected ? "Deselect All" : "Select All"}
                    </Button>
                  )}
                  {fieldsExpanded ? (
                    <ChevronUp className="h-4 w-4" />
                  ) : (
                    <ChevronDown className="h-4 w-4" />
                  )}
                </div>
              </div>
            </CardHeader>
            {fieldsExpanded && (
              <CardContent className="pt-0">
                <div className="flex justify-end mb-3">
                  <div className="flex gap-2">
                    <Button variant="outline" size="sm" onClick={handleSelectAll}>
                      Select All
                    </Button>
                    <Button variant="outline" size="sm" onClick={handleSelectNone}>
                      Select None
                    </Button>
                  </div>
                </div>
                <div className="border rounded-lg overflow-hidden">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="w-[60px]">Include</TableHead>
                        <TableHead>Field</TableHead>
                        <TableHead>Export As</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {fields.map((field) => (
                        <TableRow
                          key={field.id}
                          className={field.selected ? "" : "opacity-50"}
                        >
                          <TableCell>
                            <input
                              type="checkbox"
                              checked={field.selected}
                              onChange={() => handleFieldToggle(field.id)}
                              className="h-4 w-4 rounded border-gray-300"
                            />
                          </TableCell>
                          <TableCell>
                            <code className="text-sm">{field.field}</code>
                            {field.isRelationship && (
                              <Badge variant="outline" className="ml-2 text-xs">
                                relation
                              </Badge>
                            )}
                          </TableCell>
                          <TableCell>
                            <Input
                              value={field.as || ""}
                              onChange={(e) =>
                                handleFieldRename(field.id, e.target.value)
                              }
                              placeholder={field.label}
                              className="max-w-[200px] h-8"
                              disabled={!field.selected}
                            />
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </CardContent>
            )}
          </Card>

          {/* Filters Section */}
          <Card>
            <CardHeader
              className="pb-3 cursor-pointer"
              onClick={() => setFiltersExpanded(!filtersExpanded)}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <CardTitle className="text-base">Filters</CardTitle>
                  {filters.length > 0 && (
                    <Badge variant="secondary">{filters.length} active</Badge>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={(e) => {
                      e.stopPropagation()
                      addFilter()
                    }}
                  >
                    <Plus className="h-4 w-4 mr-1" />
                    Add Filter
                  </Button>
                  {filtersExpanded ? (
                    <ChevronUp className="h-4 w-4" />
                  ) : (
                    <ChevronDown className="h-4 w-4" />
                  )}
                </div>
              </div>
            </CardHeader>
            {filtersExpanded && (
              <CardContent className="pt-0 space-y-3">
                {filters.length === 0 ? (
                  <div className="text-center py-6 text-muted-foreground">
                    <Filter className="h-8 w-8 mx-auto mb-2 opacity-50" />
                    <p>No filters applied. Export will include all records.</p>
                    <Button
                      variant="outline"
                      size="sm"
                      className="mt-2"
                      onClick={addFilter}
                    >
                      <Plus className="h-4 w-4 mr-1" />
                      Add Filter
                    </Button>
                  </div>
                ) : (
                  filters.map((filter) => {
                    const fieldConfig = fields.find((f) => f.field === filter.field)
                    const isDateField = fieldConfig?.type === "date"

                    return (
                      <div
                        key={filter.id}
                        className="flex items-center gap-2 p-3 border rounded-lg bg-muted/30"
                      >
                        <Select
                          value={filter.field}
                          onChange={(e) =>
                            updateFilter(filter.id, { field: e.target.value })
                          }
                          className="w-[180px]"
                        >
                          {fields.map((f) => (
                            <option key={f.id} value={f.field}>
                              {f.label}
                            </option>
                          ))}
                        </Select>

                        <Select
                          value={filter.operator}
                          onChange={(e) =>
                            updateFilter(filter.id, { operator: e.target.value })
                          }
                          className="w-[160px]"
                        >
                          {FILTER_OPERATORS.map((op) => (
                            <option key={op.value} value={op.value}>
                              {op.label}
                            </option>
                          ))}
                        </Select>

                        {isDateField && filter.useRelativeDate ? (
                          <Select
                            value={filter.value}
                            onChange={(e) =>
                              updateFilter(filter.id, { value: e.target.value })
                            }
                            className="flex-1"
                          >
                            {RELATIVE_DATE_OPTIONS.map((opt) => (
                              <option key={opt.value} value={opt.value}>
                                {opt.label}
                              </option>
                            ))}
                          </Select>
                        ) : (
                          <Input
                            value={filter.value.startsWith("relative:") ? "" : filter.value}
                            onChange={(e) =>
                              updateFilter(filter.id, {
                                value: e.target.value,
                                useRelativeDate: false,
                              })
                            }
                            placeholder="Value"
                            type={isDateField ? "date" : "text"}
                            className="flex-1"
                          />
                        )}

                        {isDateField && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() =>
                              updateFilter(filter.id, {
                                useRelativeDate: !filter.useRelativeDate,
                                value: filter.useRelativeDate
                                  ? ""
                                  : "relative:last_30_days",
                              })
                            }
                          >
                            {filter.useRelativeDate ? "Use date" : "Use relative"}
                          </Button>
                        )}

                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => removeFilter(filter.id)}
                        >
                          <X className="h-4 w-4" />
                        </Button>
                      </div>
                    )
                  })
                )}
              </CardContent>
            )}
          </Card>

          {/* Save Section */}
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-end gap-4">
                <div className="flex-1">
                  <Label htmlFor="jobName" className="text-sm text-muted-foreground">
                    Job Name (required to save)
                  </Label>
                  <Input
                    id="jobName"
                    value={jobName}
                    onChange={(e) => setJobName(e.target.value)}
                    placeholder={`${selectedEntity?.label || entity} Export`}
                    className="mt-1"
                  />
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Actions */}
          <div className="flex items-center justify-between pt-2">
            <Button
              variant="outline"
              onClick={handlePreview}
              disabled={!canExport || previewMutation.isPending}
            >
              {previewMutation.isPending ? (
                <Spinner size="sm" className="mr-2" />
              ) : (
                <Eye className="mr-2 h-4 w-4" />
              )}
              Preview
            </Button>

            <div className="flex gap-3">
              <Button
                variant="outline"
                onClick={handleSaveJob}
                disabled={!canSave || saveMutation.isPending}
              >
                {saveMutation.isPending ? (
                  <Spinner size="sm" className="mr-2" />
                ) : (
                  <Save className="mr-2 h-4 w-4" />
                )}
                Save as Job
              </Button>

              <Button
                onClick={handleExportNow}
                disabled={!canExport || exportMutation.isPending}
              >
                {exportMutation.isPending ? (
                  <Spinner size="sm" className="mr-2" />
                ) : (
                  <Download className="mr-2 h-4 w-4" />
                )}
                Export Now
              </Button>
            </div>
          </div>
        </>
      )}

      {/* Preview Modal */}
      <Dialog open={previewOpen} onOpenChange={setPreviewOpen}>
        <DialogContent className="max-w-4xl max-h-[80vh] overflow-auto">
          <DialogHeader>
            <DialogTitle>Export Preview</DialogTitle>
            <DialogDescription>
              Showing first {previewData.length} records
            </DialogDescription>
          </DialogHeader>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  {fields
                    .filter((f) => f.selected)
                    .map((f) => (
                      <TableHead key={f.id}>{f.as || f.field}</TableHead>
                    ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {previewData.map((row, i) => (
                  <TableRow key={i}>
                    {fields
                      .filter((f) => f.selected)
                      .map((f) => (
                        <TableCell key={f.id}>
                          {String(row[f.as || f.field] ?? "")}
                        </TableCell>
                      ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
