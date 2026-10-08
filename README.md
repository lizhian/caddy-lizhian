# lizhian-caddy

[![Build and publish Caddy](https://github.com/lizhian/lizhian-caddy/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/lizhian/lizhian-caddy/actions/workflows/docker-publish.yml)

自动构建并发布包含以下插件的 Caddy Docker 镜像：

| 插件 | 功能 |
|---|---|
| [forwardproxy](https://github.com/caddyserver/forwardproxy) | HTTP / HTTPS 正向代理 |
| [caddy-l4](https://github.com/mholt/caddy-l4) | TCP / UDP 四层处理和 SOCKS5 代理 |
| [cloudflare](https://github.com/caddy-dns/cloudflare) | Cloudflare DNS 验证与自动签发 TLS 证书 |

镜像地址：**`ghcr.io/lizhian/lizhian-caddy`**，支持 `linux/amd64` 和 `linux/arm64`。

```bash
docker pull ghcr.io/lizhian/lizhian-caddy:latest
docker run --rm ghcr.io/lizhian/lizhian-caddy:latest caddy version
docker run --rm ghcr.io/lizhian/lizhian-caddy:latest caddy list-modules --versions
```

## 自动更新与发布

- 每天北京时间 **03:17** 自动构建；GitHub 的定时任务可能延迟执行。
- 推送构建相关文件到 `main` 或在 Actions 页面点击 **Run workflow** 也会触发。
- Caddy 使用 GitHub **最新正式稳定版**，排除 beta / rc。
- 三个插件使用各自仓库**默认分支最新提交**，包括尚未打版本标签的更新。
- 每轮开始时解析具体版本和完整提交 SHA，两个架构共用同一组版本。
- 发布前，在两个架构的最终镜像中检查 Caddy 版本、插件注册以及 HTTP / HTTPS / SOCKS5 配置能否加载。
- 每次成功发布后，自动更新 [`build-info.json`](build-info.json)，记录版本、提交、镜像 digest 和构建链接。该提交也保持仓库活跃，避免公开仓库的定时工作流因长时间无活动而被停用；机器人提交不会递归触发构建。
- 使用仓库自带的 `GITHUB_TOKEN` 发布到 GHCR，无需额外配置个人访问令牌。

最新正式 Caddy release 对应的官方 Docker `-builder` / `-alpine` 标签需要已上线。若官方 Docker 标签暂未同步，或插件最新提交与 Caddy 不兼容，当次构建会失败并保留上一次成功发布的 `latest`；后续定时构建继续尝试。

## 镜像标签

| 标签 | 含义 |
|---|---|
| `latest` | 最近一次成功构建 |
| `2`、`2.11`、`2.11.7` 等 | 对应 Caddy 版本的最近一次插件构建；版本号自动生成 |
| `build-<run_id>-<run_attempt>` | 某一次构建的独立标签 |

Caddy 版本标签会随插件或基础镜像更新。需要锁定部署内容时，使用独立构建标签或 `build-info.json` 中的 digest。

## HTTP / HTTPS / SOCKS5 示例

镜像只提供插件；需要通过 Caddyfile 启用服务。`examples/` 提供带认证的三个入口：

| 入口 | 端口 |
|---|---|
| HTTP 代理 | TCP 35890 |
| HTTPS 代理（客户端到代理服务器也使用 TLS） | TCP 35891；UDP 35891 用于 HTTP/3 |
| SOCKS5 代理 | TCP 35892 |

```bash
git clone https://github.com/lizhian/lizhian-caddy.git
cd lizhian-caddy/examples
cp proxy.env.example .env
chmod 600 .env
# 编辑 .env，填写域名、随机代理密码和 Cloudflare DNS API token
docker compose up -d
```

域名需要直接指向服务器，Cloudflare token 需要相应区域的 DNS 编辑权限。HTTPS 证书通过 DNS-01 验证自动签发和续期。

三个入口共用配置的用户名和密码。HTTP / HTTPS 代理只允许访问目标端口 80、443；示例 SOCKS5 仅启用 TCP CONNECT。SOCKS5 UDP ASSOCIATE 需要额外处理动态中继端口，不能只映射 UDP 35892。

HTTP 和原生 SOCKS5 入口本身不加密；公网访问优先选择支持 TLS 代理传输的客户端和 HTTPS 入口。HTTPS 网站也可以通过 HTTP 代理的 CONNECT 隧道访问。

升级运行中的容器：

```bash
docker compose pull
docker compose up -d
```

## 本地构建

默认使用 Caddy 和三个插件的最新 Go module 版本：

```bash
docker build -t lizhian-caddy .
```

Actions 会进一步解析插件默认分支最新提交并通过 build args 固定当次构建的输入。`Dockerfile` 支持 `CADDY_VERSION`、`CADDY_BUILDER_IMAGE`、`CADDY_RUNTIME_IMAGE`、`FORWARDPROXY_REF`、`CADDY_L4_REF`、`CLOUDFLARE_REF` 参数。

Actions 引用固定提交 SHA，并通过 Dependabot 提交月度更新提案。
