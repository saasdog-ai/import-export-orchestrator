import { useState, useRef, useEffect } from "react"
import { useNavigate, useSearchParams } from "react-router-dom"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Select } from "@/components/ui/select"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Spinner } from "@/components/ui/spinner"
import { useSchema } from "@/hooks/useSchema"
import { uploadImportFile, previewImport, executeImport, getJob } from "@/api/client"
import type { ExportEntity, ImportPreviewRecord, SchemaField } from "@/types"
import {
  ArrowLeft,
  ArrowRight,
  Upload,
  FileUp,
  CheckCircle,
  XCircle,
  AlertTriangle,
} from "lucide-react"

type Step = "upload" | "mapping" | "preview" | "execute"

interface FieldMapping {
  source: string
  target: string
}

export function ImportCreate() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [searchParams] = useSearchParams()
  const cloneJobId = searchParams.get("clone")
  const { data: schema, isLoading: schemaLoading } = useSchema()
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Fetch job to clone if cloneJobId is present
  const { data: cloneSource, isLoading: cloneLoading } = useQuery({
    queryKey: ["job", cloneJobId],
    queryFn: () => getJob(cloneJobId!),
    enabled: !!cloneJobId,
  })

  const [step, setStep] = useState<Step>("upload")
  const [entity, setEntity] = useState<ExportEntity | "">("")
  const isCloning = !!cloneJobId

  // Initialize entity from clone source
  useEffect(() => {
    if (cloneSource?.import_config?.entity) {
      setEntity(cloneSource.import_config.entity)
    }
  }, [cloneSource])
  const [file, setFile] = useState<File | null>(null)
  const [filePath, setFilePath] = useState("")
  const [sourceColumns, setSourceColumns] = useState<string[]>([])
  const [fieldMappings, setFieldMappings] = useState<FieldMapping[]>([])
  const [previewRecords, setPreviewRecords] = useState<ImportPreviewRecord[]>([])
  const [validCount, setValidCount] = useState(0)
  const [invalidCount, setInvalidCount] = useState(0)

  const selectedEntity = schema?.entities.find((e) => e.name === entity)

  const uploadMutation = useMutation({
    mutationFn: ({ file, entity }: { file: File; entity: string }) =>
      uploadImportFile(file, entity),
    onSuccess: (data) => {
      setFilePath(data.file_path)
      // For now, we'll get columns from the preview
      setStep("mapping")
    },
  })

  const previewMutation = useMutation({
    mutationFn: previewImport,
    onSuccess: (data) => {
      setPreviewRecords(data.records)
      setValidCount(data.valid_count)
      setInvalidCount(data.invalid_count)

      // Extract source columns from first record
      if (data.records.length > 0) {
        const cols = Object.keys(data.records[0].data)
        setSourceColumns(cols)

        // Auto-map fields if not already done
        if (fieldMappings.length === 0 && selectedEntity) {
          const autoMappings: FieldMapping[] = []
          cols.forEach((col) => {
            // Try to find a matching target field
            const normalizedCol = col.toLowerCase().replace(/[_\s]/g, "")
            const matchingField = selectedEntity.fields.find((f: SchemaField) => {
              const normalizedTarget = f.name.toLowerCase().replace(/[_\s]/g, "")
              const normalizedLabel = f.label.toLowerCase().replace(/[_\s]/g, "")
              return normalizedTarget === normalizedCol || normalizedLabel === normalizedCol
            })

            if (matchingField) {
              autoMappings.push({ source: col, target: matchingField.name })
            }
          })
          setFieldMappings(autoMappings)
        }
      }

      setStep("preview")
    },
  })

  const executeMutation = useMutation({
    mutationFn: executeImport,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["jobs"] })
      navigate(`/jobs/${data.job_id}`)
    },
  })

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0]
    if (selectedFile) {
      setFile(selectedFile)
    }
  }

  const handleUpload = () => {
    if (file && entity) {
      uploadMutation.mutate({ file, entity })
    }
  }

  const handleMappingChange = (source: string, target: string) => {
    setFieldMappings((prev) => {
      const existing = prev.find((m) => m.source === source)
      if (existing) {
        if (target === "") {
          return prev.filter((m) => m.source !== source)
        }
        return prev.map((m) => (m.source === source ? { ...m, target } : m))
      }
      return [...prev, { source, target }]
    })
  }

  const handlePreview = () => {
    previewMutation.mutate({
      file_path: filePath,
      entity: entity as ExportEntity,
      field_mappings: fieldMappings.length > 0 ? fieldMappings : undefined,
    })
  }

  const handleExecute = () => {
    executeMutation.mutate({
      file_path: filePath,
      entity: entity as ExportEntity,
      field_mappings: fieldMappings.length > 0 ? fieldMappings : undefined,
    })
  }

  if (schemaLoading || cloneLoading) {
    return (
      <div className="flex justify-center py-12">
        <Spinner size="lg" />
      </div>
    )
  }

  return (
    <div className="space-y-8">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate(-1)}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div>
          <h1 className="text-3xl font-bold tracking-tight">
            {isCloning ? "Clone Import" : "Import Data"}
          </h1>
          <p className="text-muted-foreground">
            {isCloning
              ? `Cloning from "${cloneSource?.name}" - upload a new file for import`
              : "Upload and import data from a file"}
          </p>
        </div>
      </div>

      {/* Step indicator */}
      <div className="flex items-center gap-2 text-sm">
        {(["upload", "mapping", "preview", "execute"] as Step[]).map((s, i) => (
          <div key={s} className="flex items-center">
            {i > 0 && <div className="mx-2 h-px w-8 bg-border" />}
            <div
              className={`flex h-8 w-8 items-center justify-center rounded-full ${
                step === s
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted text-muted-foreground"
              }`}
            >
              {i + 1}
            </div>
            <span
              className={`ml-2 capitalize ${
                step === s ? "font-medium" : "text-muted-foreground"
              }`}
            >
              {s}
            </span>
          </div>
        ))}
      </div>

      {/* Step 1: Upload */}
      {step === "upload" && (
        <Card>
          <CardHeader>
            <CardTitle>Upload File</CardTitle>
            <CardDescription>
              Select an entity type and upload your CSV or Excel file
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="space-y-2">
              <Label htmlFor="entity">Entity Type</Label>
              <Select
                id="entity"
                value={entity}
                onChange={(e) => setEntity(e.target.value as ExportEntity)}
              >
                <option value="">Select an entity...</option>
                {schema?.entities.map((e) => (
                  <option key={e.name} value={e.name}>
                    {e.label}
                  </option>
                ))}
              </Select>
            </div>

            <div className="space-y-2">
              <Label>File</Label>
              <div
                className="border-2 border-dashed rounded-lg p-8 text-center cursor-pointer hover:border-primary/50 transition-colors"
                onClick={() => fileInputRef.current?.click()}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".csv,.xlsx,.xls"
                  onChange={handleFileSelect}
                  className="hidden"
                />
                {file ? (
                  <div className="flex flex-col items-center gap-2">
                    <FileUp className="h-8 w-8 text-primary" />
                    <p className="font-medium">{file.name}</p>
                    <p className="text-sm text-muted-foreground">
                      {(file.size / 1024).toFixed(1)} KB
                    </p>
                  </div>
                ) : (
                  <div className="flex flex-col items-center gap-2">
                    <Upload className="h-8 w-8 text-muted-foreground" />
                    <p className="font-medium">Click to upload</p>
                    <p className="text-sm text-muted-foreground">
                      CSV or Excel files up to 10MB
                    </p>
                  </div>
                )}
              </div>
            </div>

            <div className="flex justify-end">
              <Button
                onClick={handleUpload}
                disabled={!entity || !file || uploadMutation.isPending}
              >
                {uploadMutation.isPending ? (
                  <Spinner size="sm" className="mr-2" />
                ) : (
                  <ArrowRight className="mr-2 h-4 w-4" />
                )}
                Continue
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Step 2: Field Mapping */}
      {step === "mapping" && (
        <Card>
          <CardHeader>
            <CardTitle>Map Fields</CardTitle>
            <CardDescription>
              Map columns from your file to the target fields. We've auto-mapped
              some fields based on column names.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Source Column</TableHead>
                  <TableHead>Target Field</TableHead>
                  <TableHead>Required</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sourceColumns.length > 0 ? (
                  sourceColumns.map((col) => {
                    const mapping = fieldMappings.find((m) => m.source === col)
                    const targetField = selectedEntity?.fields.find(
                      (f: SchemaField) => f.name === mapping?.target
                    )

                    return (
                      <TableRow key={col}>
                        <TableCell>
                          <code className="rounded bg-muted px-1.5 py-0.5 text-sm">
                            {col}
                          </code>
                        </TableCell>
                        <TableCell>
                          <Select
                            value={mapping?.target || ""}
                            onChange={(e) =>
                              handleMappingChange(col, e.target.value)
                            }
                            className="max-w-[200px]"
                          >
                            <option value="">-- Skip this column --</option>
                            {selectedEntity?.fields.map((f: SchemaField) => (
                              <option key={f.name} value={f.name}>
                                {f.label}
                              </option>
                            ))}
                          </Select>
                        </TableCell>
                        <TableCell>
                          {targetField?.required ? (
                            <Badge variant="destructive">Required</Badge>
                          ) : (
                            <Badge variant="secondary">Optional</Badge>
                          )}
                        </TableCell>
                      </TableRow>
                    )
                  })
                ) : (
                  <TableRow>
                    <TableCell colSpan={3} className="text-center py-8">
                      <p className="text-muted-foreground">
                        Preview the file to see source columns
                      </p>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>

            <div className="flex justify-between">
              <Button variant="outline" onClick={() => setStep("upload")}>
                <ArrowLeft className="mr-2 h-4 w-4" />
                Back
              </Button>
              <Button
                onClick={handlePreview}
                disabled={previewMutation.isPending}
              >
                {previewMutation.isPending ? (
                  <Spinner size="sm" className="mr-2" />
                ) : null}
                Preview Import
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Step 3: Preview */}
      {step === "preview" && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Preview Import</CardTitle>
                <CardDescription>
                  Review the data before importing
                </CardDescription>
              </div>
              <div className="flex gap-4">
                <div className="flex items-center gap-2 text-green-600">
                  <CheckCircle className="h-5 w-5" />
                  <span className="font-medium">{validCount} valid</span>
                </div>
                <div className="flex items-center gap-2 text-red-600">
                  <XCircle className="h-5 w-5" />
                  <span className="font-medium">{invalidCount} invalid</span>
                </div>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="overflow-x-auto rounded-lg border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[60px]">Row</TableHead>
                    <TableHead className="w-[80px]">Status</TableHead>
                    {fieldMappings.map((m) => (
                      <TableHead key={m.source}>{m.target}</TableHead>
                    ))}
                    <TableHead>Errors</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {previewRecords.map((record) => (
                    <TableRow
                      key={record.row}
                      className={record.is_valid ? "" : "bg-red-50"}
                    >
                      <TableCell>{record.row}</TableCell>
                      <TableCell>
                        {record.is_valid ? (
                          <CheckCircle className="h-4 w-4 text-green-600" />
                        ) : (
                          <XCircle className="h-4 w-4 text-red-600" />
                        )}
                      </TableCell>
                      {fieldMappings.map((m) => (
                        <TableCell key={m.source}>
                          {String(record.data[m.target] ?? "")}
                        </TableCell>
                      ))}
                      <TableCell>
                        {record.errors.length > 0 && (
                          <div className="flex flex-col gap-1">
                            {record.errors.map((err, i) => (
                              <span
                                key={i}
                                className="text-xs text-red-600"
                              >
                                {err.field}: {err.message}
                              </span>
                            ))}
                          </div>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>

            {invalidCount > 0 && (
              <div className="flex items-start gap-2 rounded-lg border border-yellow-200 bg-yellow-50 p-4">
                <AlertTriangle className="h-5 w-5 text-yellow-600 shrink-0" />
                <div>
                  <p className="font-medium text-yellow-800">
                    Some records have validation errors
                  </p>
                  <p className="text-sm text-yellow-700">
                    Invalid records will be skipped during import. You can go
                    back and adjust your field mappings or proceed with valid
                    records only.
                  </p>
                </div>
              </div>
            )}

            <div className="flex justify-between">
              <Button variant="outline" onClick={() => setStep("mapping")}>
                <ArrowLeft className="mr-2 h-4 w-4" />
                Back
              </Button>
              <Button
                onClick={() => setStep("execute")}
                disabled={validCount === 0}
              >
                Continue
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Step 4: Execute */}
      {step === "execute" && (
        <Card>
          <CardHeader>
            <CardTitle>Execute Import</CardTitle>
            <CardDescription>
              Review and confirm your import settings
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="rounded-lg border p-4 space-y-3">
              <h4 className="font-medium">Import Summary</h4>
              <div className="grid gap-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Entity:</span>
                  <span>{selectedEntity?.label || entity}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">File:</span>
                  <span>{file?.name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Total Records:</span>
                  <span>{validCount + invalidCount}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">
                    Records to Import:
                  </span>
                  <span className="text-green-600 font-medium">
                    {validCount}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">
                    Records to Skip:
                  </span>
                  <span className="text-red-600 font-medium">
                    {invalidCount}
                  </span>
                </div>
              </div>
            </div>

            <div className="rounded-lg border p-4 space-y-3">
              <h4 className="font-medium">Field Mappings</h4>
              <div className="grid gap-1 text-sm">
                {fieldMappings.map((m) => (
                  <div key={m.source} className="flex items-center gap-2">
                    <code className="rounded bg-muted px-1.5 py-0.5">
                      {m.source}
                    </code>
                    <ArrowRight className="h-3 w-3 text-muted-foreground" />
                    <span>{m.target}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="flex justify-between">
              <Button variant="outline" onClick={() => setStep("preview")}>
                <ArrowLeft className="mr-2 h-4 w-4" />
                Back
              </Button>
              <Button
                onClick={handleExecute}
                disabled={executeMutation.isPending || validCount === 0}
              >
                {executeMutation.isPending ? (
                  <Spinner size="sm" className="mr-2" />
                ) : (
                  <Upload className="mr-2 h-4 w-4" />
                )}
                Execute Import
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
