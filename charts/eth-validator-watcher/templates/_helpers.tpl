{{/*
Expand the name of the chart.
*/}}
{{- define "ethereum-validator-watcher.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "ethereum-validator-watcher.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "ethereum-validator-watcher.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "ethereum-validator-watcher.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "ethereum-validator-watcher.fullname" .) .Values.serviceAccount.name }}
{{- else }}

{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "ethereum-validator-watcher.labels" -}}
app.kubernetes.io/name: {{ include "ethereum-validator-watcher.name" . }}
helm.sh/chart: {{ include "ethereum-validator-watcher.chart" . }}
app.kubernetes.io/instance: ethereum-validator-watcher
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
{{- end -}}

{{/*
Selector labels
*/}}
{{- define "ethereum-validator-watcher.matchLabels" -}}
app.kubernetes.io/name: {{ include "ethereum-validator-watcher.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}
