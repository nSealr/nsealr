import { type ServiceContextFileOptions } from "./context.js";
export declare function loadPublicS3Context(options: ServiceContextFileOptions): Promise<{
    context: import("@nsealr/client").LocalServiceContext;
    connectionId: string;
    arm(): void;
    check(): void;
    close(): Promise<void>;
}>;
