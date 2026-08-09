{{- define "liftosaur2garmin.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "liftosaur2garmin.fullname" -}}
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

{{- define "liftosaur2garmin.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "liftosaur2garmin.selectorLabels" -}}
app.kubernetes.io/name: {{ include "liftosaur2garmin.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{- define "liftosaur2garmin.labels" -}}
helm.sh/chart: {{ include "liftosaur2garmin.chart" . }}
{{ include "liftosaur2garmin.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{- define "liftosaur2garmin.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "liftosaur2garmin.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{- define "liftosaur2garmin.secretName" -}}
{{- if .Values.secret.create }}
{{- include "liftosaur2garmin.fullname" . }}
{{- else }}
{{- .Values.secret.existingSecret }}
{{- end }}
{{- end }}

{{- define "liftosaur2garmin.pvcName" -}}
{{- default (include "liftosaur2garmin.fullname" .) .Values.persistence.existingClaim }}
{{- end }}

{{- define "liftosaur2garmin.configData" -}}
{{- $data := dict -}}
{{- range $key, $value := .Values.config -}}
{{- if ne (toString $value) "" -}}
{{- $_ := set $data $key (toString $value) -}}
{{- end -}}
{{- end -}}
{{- if $data -}}
{{- toYaml $data -}}
{{- end -}}
{{- end }}
