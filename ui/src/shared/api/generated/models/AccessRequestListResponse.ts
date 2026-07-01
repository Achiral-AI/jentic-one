/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AccessRequestResponse } from './AccessRequestResponse';
/**
 * Paginated list of access requests.
 */
export type AccessRequestListResponse = {
    data: Array<AccessRequestResponse>;
    has_more: boolean;
    next_cursor?: (string | null);
};

