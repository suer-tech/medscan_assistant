import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Plus, Trash2, Settings2, FileText, ClipboardList, CheckCircle2 } from "lucide-react";
import { cn } from "@/lib/utils";

export interface TemplateField {
  name: string;
  value: string;
  included: boolean;
  fieldType?: "text" | "select";
  options?: string[];
  section?: "input" | "structure" | "conclusion";
  aiValue?: string; // Значение от ИИ для двухколоночных полей
}

interface TemplateFormFieldsProps {
  fields: TemplateField[];
  onChange: (fields: TemplateField[]) => void;
}

export default function TemplateFormFields({ fields, onChange }: TemplateFormFieldsProps) {
  const updateField = (index: number, updates: Partial<TemplateField>) => {
    const newFields = [...fields];
    newFields[index] = { ...newFields[index], ...updates };
    onChange(newFields);
  };

  const addField = () => {
    onChange([...fields, { name: "", value: "", included: true }]);
  };

  const removeField = (index: number) => {
    onChange(fields.filter((_, i) => i !== index));
  };

  // Разделяем поля по секциям
  const inputFields = fields.filter((f, i) => i < 16); // Поля 0-15 (теперь 16 полей)
  const structureFields = fields.filter((f, i) => i >= 16 && i < 32); // Поля 16-31
  const conclusionFields = fields.filter((f, i) => i >= 32); // Поля 32-37

  // Группируем входные данные по подразделам
  const deviceName = inputFields.slice(0, 1); // Поле 0 - Название прибора
  const deviceParams = inputFields.slice(1, 3); // Поля 1-2 - Модель ОСТ и Режим сканирования
  const scanParams = inputFields.slice(3, 9); // Поля 3-8
  const imageParams = inputFields.slice(9, 13); // Поля 9-12
  const operatorComments = inputFields.slice(13, 16); // Поля 13-15

  const renderInputField = (field: TemplateField, index: number, isTwoColumn = false, showLabel = false) => {
    return (
      <div className={cn("space-y-1.5", isTwoColumn && "h-full")}>
        {showLabel && (
          <Label htmlFor={`field-${index}`} className="text-sm font-medium text-foreground">
            {field.name}
          </Label>
        )}
        {field.fieldType === "select" && field.options ? (
          <Select
            value={field.value}
            onValueChange={(value) => updateField(index, { value })}
          >
            <SelectTrigger className="w-full" id={`field-${index}`}>
              <SelectValue placeholder="Выберите значение" />
            </SelectTrigger>
            <SelectContent>
              {field.options.map((option) => (
                <SelectItem key={option} value={option}>
                  {option}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        ) : isTwoColumn ? (
          <Textarea
            id={`field-${index}`}
            placeholder="Введите значение врача"
            value={field.value}
            onChange={(e) => updateField(index, { value: e.target.value })}
            rows={3}
            className="resize-none"
          />
        ) : (
          <Input
            id={`field-${index}`}
            placeholder="Введите значение или оставьте пустым"
            value={field.value}
            onChange={(e) => updateField(index, { value: e.target.value })}
          />
        )}
        {isTwoColumn && field.aiValue && (
          <div className="mt-2 p-3 bg-blue-50 border border-blue-200 rounded-md">
            <div className="flex items-start gap-2">
              <CheckCircle2 className="h-4 w-4 text-blue-600 mt-0.5 flex-shrink-0" />
              <div className="flex-1">
                <Label className="text-xs font-medium text-blue-900 mb-1 block">
                  Ответ ИИ:
                </Label>
                <p className="text-sm text-blue-800">{field.aiValue}</p>
              </div>
            </div>
          </div>
        )}
      </div>
    );
  };

  const renderTwoColumnField = (field: TemplateField, index: number) => {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-1.5">
          <div className="flex items-center gap-2">
            <FileText className="h-4 w-4 text-muted-foreground" />
            <Label className="text-sm font-medium text-muted-foreground">
              Врач
            </Label>
          </div>
          <Textarea
            id={`field-${index}`}
            placeholder="Введите значение врача"
            value={field.value}
            onChange={(e) => updateField(index, { value: e.target.value })}
            rows={3}
            className="resize-none"
          />
        </div>
        <div className="space-y-1.5">
          <div className="flex items-center gap-2">
            <ClipboardList className="h-4 w-4 text-blue-600" />
            <Label className="text-sm font-medium text-blue-600">
              ИИ
            </Label>
          </div>
          {field.aiValue ? (
            <Textarea
              value={field.aiValue}
              readOnly
              rows={3}
              className="resize-none bg-blue-50 border-blue-200 text-blue-800 cursor-default"
            />
          ) : (
            <Textarea
              value=""
              readOnly
              rows={3}
              placeholder="Будет заполнено после анализа"
              className="resize-none bg-muted/30 border-dashed text-muted-foreground cursor-default"
            />
          )}
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-6">
      {/* ========== ВХОДНЫЕ ДАННЫЕ ========== */}
      <Card className="border-2 overflow-hidden p-0">
        <CardHeader className="bg-gradient-to-r from-blue-50 to-indigo-50 border-b px-6 py-4 m-0 rounded-t-xl">
          <CardTitle className="text-lg font-semibold flex items-center gap-2">
            <Settings2 className="h-5 w-5 text-blue-600" />
            Входные данные
          </CardTitle>
        </CardHeader>
        <CardContent className="pt-4 pb-6 space-y-5">
          {/* Параметры прибора */}
          <div className="space-y-3">
            <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide flex items-center gap-2 pb-2 border-b">
              <div className="h-1.5 w-1.5 rounded-full bg-blue-500"></div>
              Параметры прибора
            </h3>
            
            {/* Поля прибора в сетке 1-2 колонки */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {deviceName.map((field, idx) => {
                const globalIndex = idx;
                return (
                  <div key={globalIndex} className="space-y-1.5">
                    {renderInputField(field, globalIndex, false, true)}
                  </div>
                );
              })}
              {deviceParams.map((field, idx) => {
                const globalIndex = idx + 1;
                return (
                  <div key={globalIndex} className="space-y-1.5">
                    {renderInputField(field, globalIndex, false, true)}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Параметры сканирования */}
          <div className="space-y-3">
            <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide flex items-center gap-2 pb-2 border-b">
              <div className="h-1.5 w-1.5 rounded-full bg-cyan-500"></div>
              Параметры сканирования
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {scanParams.map((field, idx) => {
                const globalIndex = idx + 3;
                return (
                  <div key={globalIndex} className="space-y-1.5">
                    {renderInputField(field, globalIndex, false, true)}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Параметры изображения */}
          <div className="space-y-3">
            <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide flex items-center gap-2 pb-2 border-b">
              <div className="h-1.5 w-1.5 rounded-full bg-purple-500"></div>
              Параметры изображения
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {imageParams.map((field, idx) => {
                const globalIndex = idx + 9;
                return (
                  <div key={globalIndex} className="space-y-1.5">
                    {renderInputField(field, globalIndex, false, true)}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Комментарии оператора */}
          <div className="space-y-3">
            <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide flex items-center gap-2 pb-2 border-b">
              <div className="h-1.5 w-1.5 rounded-full bg-amber-500"></div>
              Комментарии оператора исследования
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {operatorComments.map((field, idx) => {
                const globalIndex = idx + 13;
                return (
                  <div key={globalIndex} className="space-y-1.5">
                    {renderInputField(field, globalIndex, false, true)}
                  </div>
                );
              })}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* ========== ОПИСАНИЕ СТРУКТУРЫ СЕТЧАТКИ И АНАЛИЗ ПАТТЕРНОВ ========== */}
      <Card className="border-2 overflow-hidden p-0">
        <CardHeader className="bg-gradient-to-r from-green-50 to-emerald-50 border-b px-6 py-4 m-0 rounded-t-xl">
          <CardTitle className="text-lg font-semibold flex items-center gap-2">
            <FileText className="h-5 w-5 text-green-600" />
            Описание структуры сетчатки (по OCT) и Анализ паттернов
          </CardTitle>
        </CardHeader>
        <CardContent className="pt-4 pb-6 space-y-4">
          {structureFields.map((field, idx) => {
            const globalIndex = idx + 16;
            return (
              <div key={globalIndex} className="space-y-2 p-4 border rounded-lg hover:bg-muted/30 transition-colors">
                <Label className="text-sm font-medium text-foreground">
                  {field.name}
                </Label>
                {renderTwoColumnField(field, globalIndex)}
              </div>
            );
          })}
        </CardContent>
      </Card>

      {/* ========== ЗАКЛЮЧЕНИЕ ========== */}
      <Card className="border-2 overflow-hidden p-0">
        <CardHeader className="bg-gradient-to-r from-purple-50 to-pink-50 border-b px-6 py-4 m-0 rounded-t-xl">
          <CardTitle className="text-lg font-semibold flex items-center gap-2">
            <CheckCircle2 className="h-5 w-5 text-purple-600" />
            Заключение
          </CardTitle>
        </CardHeader>
        <CardContent className="pt-4 pb-6 space-y-4">
          {conclusionFields.map((field, idx) => {
            const globalIndex = idx + 32;
            return (
              <div key={globalIndex} className="space-y-2 p-4 border rounded-lg hover:bg-muted/30 transition-colors">
                <Label className="text-sm font-medium text-foreground">
                  {field.name}
                </Label>
                {renderTwoColumnField(field, globalIndex)}
              </div>
            );
          })}
        </CardContent>
      </Card>
    </div>
  );
}
