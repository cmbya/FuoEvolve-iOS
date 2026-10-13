# FuoEvolve iOS unsigned builder

本仓库仅维护构建工作流和打包脚本，不复制上游应用源码。

在 Actions 中手动运行 **Build unsigned FuoEvolve IPA**，输入上游 `feeluown/FuoEvolve` 的 tag/branch/commit（默认 master）。工作流在 macOS runner 拉取上游，使用 JDK 17 和 Xcode 构建 iPhone ARM64 Release 应用，再打包未签名 IPA。实际源码 SHA 和工具版本随产物提供。

下载 `FuoEvolve-iOS-unsigned` artifact。签名、安装由用户处理。编译成功不等于所有真机功能通过；失败日志保存在 `build-logs` artifact。

仅手动触发，尚未设置定时更新。上游项目 GPL-3.0，应用产物遵循上游许可证；保留构建来源以便获取对应源码。未修改上游仓库。
