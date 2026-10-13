# FuoEvolve iOS unsigned builder

本仓库仅维护构建工作流、打包脚本和局部源码补丁，不复制完整上游应用源码。

在 Actions 中手动运行 **Build unsigned FuoEvolve IPA**，输入上游 `feeluown/FuoEvolve` 的 tag/branch/commit（默认固定 `7e271c262c6c5495be5d1b680748ac4ba9e5bf0e`）。工作流在 macOS runner 拉取上游，使用 JDK 17 和 Xcode 构建 iPhone ARM64 Release 应用，再打包未签名 IPA。实际源码 SHA 和工具版本随产物提供。

下载 `FuoEvolve-iOS-unsigned` artifact。签名、安装由用户处理。编译成功不等于所有真机功能通过；失败日志保存在 `build-logs` artifact。

仅手动触发，尚未设置定时更新。上游项目 GPL-3.0，应用产物和局部修改遵循上游许可证；保留构建来源以便获取对应源码。未修改上游仓库。

## iOS 登录补丁（只修复，尚未编译/真机验证）

工作流拉取上游后运行 `python3 scripts/patch-provider-login.py upstream`。脚本先校验两份目标源码的 SHA-256，再替换精确锚定的局部块；源码漂移或重复应用会失败，不会默默套错。其他 ref 仅在目标文件完全相同时可用。

- Keychain：移除 Kotlin Map→CPointer 的直接强转；创建原生 CF 字典，显式 retain/release 字符串、NSData 和查询对象，正确转移 Copy 返回值的所有权。`kSecMatchLimit` 仅用于读取；更新优先，不先删除旧凭据。服务名、账号和 JSON 格式保持兼容，不改为明文设置。
- QQ/网易：首次请求前设置桌面 Safari UA 与 desktop content mode，让已有网页版登录入口可见；不新增短信 API。
- Bilibili：保留默认移动 UA，明确 mobile content mode；不改现有手机号/短信网页流程。页面完成和 Cookie 变化时检查凭据并自动回传。
- Cookie：按 provider 根域及点边界筛选，排除空值与过期 Cookie；未知 provider 拒绝导入。必须满足配置的完整 Cookie 组；手动“完成”不足时显示提示，自动与取消/滑动关闭只回调一次。窗口打开复用当前 WebView，不额外发登录 API 请求，不记录凭据。

本地静态回归：`python3 -m unittest discover -s tests -v`。默认使用相邻只读 `FuoEvolve-upstream`，可用 `FUO_UPSTREAM=/path/to/pinned/checkout` 指定。测试实际在 scratch 临时副本上执行补丁，验证原始错误强转、域边界、漂移拒绝和无关代码保留。域匹配真值表是 Python 静态模型，不冒充 Swift/WebKit 运行测试。

桥接 API 参考：
- [multiplatform-settings KeychainSettings.kt](https://github.com/russhwolf/multiplatform-settings/blob/main/multiplatform-settings/src/appleMain/kotlin/com/russhwolf/settings/KeychainSettings.kt)：原生 CF 字典、CFBridgingRetain、CFTypeRefVar、CFBridgingRelease 和 SecItemUpdate 的 Kotlin/Native 用法。
- [Apple CFBridgingRelease](https://developer.apple.com/documentation/foundation/cfbridgingrelease)：Copy/Retain 所有权移交 ARC。
- [Apple SecItemCopyMatching](https://developer.apple.com/documentation/security/secitemcopymatching(_:_:))：查询匹配与返回类型。

验证边界：Linux 无 Xcode，本次没有编译、触发 Actions 或真实登录。网页桌面入口显示、Bilibili 短信后 Cookie 写入时序、跨语言编译以及 Keychain 持久化仍需用户授权构建后在设备验证。Cookie 就绪不等于服务器认证成功；后续账号校验仍由原有 provider 逻辑执行。
