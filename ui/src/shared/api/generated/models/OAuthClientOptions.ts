/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * How to talk to one vendor's authorize and token endpoints.
 */
export type OAuthClientOptions = {
    keep_token_fields?: Record<string, string>;
    pkce?: boolean;
    redirect_uri?: (string | null);
    token_auth_method?: OAuthClientOptions.token_auth_method;
    token_request_encoding?: OAuthClientOptions.token_request_encoding;
};
export namespace OAuthClientOptions {
    export enum token_auth_method {
        CLIENT_SECRET_POST = 'client_secret_post',
        CLIENT_SECRET_BASIC = 'client_secret_basic',
    }
    export enum token_request_encoding {
        FORM = 'form',
        JSON = 'json',
    }
}

