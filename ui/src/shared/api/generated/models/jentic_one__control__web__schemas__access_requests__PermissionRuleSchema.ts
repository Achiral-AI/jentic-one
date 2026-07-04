/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Permission rule for an access request item.
 */
export type jentic_one__control__web__schemas__access_requests__PermissionRuleSchema = {
    effect: jentic_one__control__web__schemas__access_requests__PermissionRuleSchema.effect;
    methods?: (Array<string> | null);
    operations?: (Array<string> | null);
    path?: (string | null);
};
export namespace jentic_one__control__web__schemas__access_requests__PermissionRuleSchema {
    export enum effect {
        ALLOW = 'allow',
        DENY = 'deny',
        REQUIRE_APPROVAL = 'require-approval',
    }
}

