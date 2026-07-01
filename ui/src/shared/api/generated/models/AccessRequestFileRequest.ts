/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AccessRequestItemRequest } from './AccessRequestItemRequest';
/**
 * Request body for filing an access request.
 */
export type AccessRequestFileRequest = {
    items: Array<AccessRequestItemRequest>;
    reason?: (string | null);
};

