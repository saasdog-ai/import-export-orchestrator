import { useQuery } from "@tanstack/react-query"
import { getSchema } from "@/api/client"

export function useSchema() {
  return useQuery({
    queryKey: ["schema"],
    queryFn: getSchema,
    staleTime: 5 * 60 * 1000, // Cache schema for 5 minutes
  })
}
