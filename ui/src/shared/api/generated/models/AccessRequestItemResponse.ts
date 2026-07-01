/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Response model for a single access-request line item.
 */
export type AccessRequestItemResponse = {
    action: string;
    applied_effects?: (Record<string, any> | null);
    credential_name?: (string | null);
    decided_at?: (string | null);
    decided_by?: (string | null);
    decision_reason?: (string | null);
    id: string;
    resource_id?: (string | null);
    resource_reference?: (Record<string, any> | null);
    resource_type: string;
    rules?: null;
    status: string;
    to_id?: (string | null);
    to_type?: (string | null);
    toolkit_name?: (string | null);
};

