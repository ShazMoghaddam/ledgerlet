import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api, unwrap } from "../../api/client";
import type { ImportRowConfirm } from "../../api/types";
import type { Mapping } from "../../lib/importMapping";

/** The upload: the file plus which column is which, as the API's form fields. */
export function previewForm(file: File, mapping: Mapping): FormData {
  const form = new FormData();
  form.append("file", file);
  form.append("date_column", mapping.dateColumn);
  form.append("description_column", mapping.descriptionColumn);
  if (mapping.amountStyle === "signed") {
    form.append("amount_column", mapping.amountColumn);
    form.append("invert_sign", String(mapping.invertSign));
  } else {
    form.append("paid_in_column", mapping.paidInColumn);
    form.append("paid_out_column", mapping.paidOutColumn);
  }
  form.append("date_format", mapping.dateFormat);
  return form;
}

/** Step 1 on the server: read the file with this mapping. Nothing is saved. */
export function usePreviewImport() {
  return useMutation({
    mutationFn: async ({
      propertyId,
      file,
      mapping,
    }: {
      propertyId: string;
      file: File;
      mapping: Mapping;
    }) => {
      const form = previewForm(file, mapping);
      return unwrap(
        await api.POST("/api/v1/properties/{property_id}/imports/preview", {
          params: { path: { property_id: propertyId } },
          // A file upload: sent as multipart form data, not JSON.
          body: form as unknown as never,
          bodySerializer: (body) => body as unknown as FormData,
        }),
      );
    },
  });
}

/** Step 2: save the rows the landlord kept, all or nothing. */
export function useConfirmImport() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ propertyId, rows }: { propertyId: string; rows: ImportRowConfirm[] }) =>
      unwrap(
        await api.POST("/api/v1/properties/{property_id}/imports/confirm", {
          params: { path: { property_id: propertyId } },
          body: { rows },
        }),
      ),
    onSuccess: () =>
      Promise.all([
        queryClient.invalidateQueries({ queryKey: ["transactions"] }),
        queryClient.invalidateQueries({ queryKey: ["tax"] }),
      ]),
  });
}
