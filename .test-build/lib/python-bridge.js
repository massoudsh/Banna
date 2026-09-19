"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.PipelineError = void 0;
exports.pythonExecutable = pythonExecutable;
exports.bridgeScript = bridgeScript;
exports.isBridgeConfigured = isBridgeConfigured;
exports.runPipeline = runPipeline;
const node_child_process_1 = require("node:child_process");
const node_fs_1 = require("node:fs");
const node_path_1 = __importDefault(require("node:path"));
class PipelineError extends Error {
    constructor(message, code) {
        super(message);
        this.code = code;
        this.name = 'PipelineError';
    }
}
exports.PipelineError = PipelineError;
function projectRoot() {
    return process.env.BANNA_PROJECT_ROOT ?? process.cwd();
}
function pythonExecutable() {
    return process.env.BANNA_PYTHON ?? 'python3';
}
/** مسیر اسکریپت پل — در ریشهٔ پروژه، کنار موتورهای پایتون. */
function bridgeScript() {
    return node_path_1.default.join(projectRoot(), 'scripts', 'pipeline_json.py');
}
function isBridgeConfigured() {
    return (0, node_fs_1.existsSync)(bridgeScript());
}
/**
 * اجرای pipeline پایتون و برگرداندن خروجی ساختاریافته.
 *
 * خطاهای دامنه (`WBSError`، `ScopeError`، `MediaValidationError`) با کد ۲ بر
 * می‌گردند و پیام فارسی‌شان دست‌نخورده به UI می‌رسد؛ خطای محیطی (نبود
 * مفسر/اسکریپت) با `not_configured` مشخص می‌شود تا UI بتواند فرق بگذارد.
 */
function runPipeline(input) {
    if (!isBridgeConfigured()) {
        return Promise.reject(new PipelineError('اسکریپت پل پایتون پیدا نشد.', 'not_configured'));
    }
    const args = [bridgeScript(), '--description', input.description];
    if (input.totalAreaM2 != null && input.totalAreaM2 > 0) {
        args.push('--area', String(input.totalAreaM2));
    }
    return new Promise((resolve, reject) => {
        const child = (0, node_child_process_1.spawn)(pythonExecutable(), args, {
            cwd: projectRoot(),
            env: { ...process.env, PYTHONIOENCODING: 'utf-8' },
        });
        let stdout = '';
        let stderr = '';
        child.stdout.on('data', (chunk) => {
            stdout += chunk;
        });
        child.stderr.on('data', (chunk) => {
            stderr += chunk;
        });
        child.on('error', () => {
            reject(new PipelineError('اجرای موتور پایتون ممکن نشد.', 'not_configured'));
        });
        child.on('close', (code) => {
            if (code === 0) {
                try {
                    resolve(JSON.parse(stdout));
                }
                catch {
                    reject(new PipelineError('خروجی موتور قابل‌خواندن نبود.', 'failed'));
                }
                return;
            }
            const message = stdout.trim() || stderr.trim().split('\n').pop() || '';
            reject(new PipelineError(message || 'پردازش پروژه در موتور تخمین انجام نشد.', 'failed'));
        });
    });
}
