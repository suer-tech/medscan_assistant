"""OpenAI image analysis"""
from typing import Literal, Optional, List
import json
import re
from server._core.llm import invoke_llm, Message

StudyType = Literal[
    "retinal_scan", 
    "optic_nerve", 
    "macular_analysis", 
    "free_query", 
    "template_form",
    "ultrasound_thyroid",
    "ultrasound_liver",
    "lab_blood",
    "brain",
    "lungs",
    "bone",
    "eye"
]

STUDY_TYPE_PROMPTS = {
    "retinal_scan": """Вы - опытный офтальмолог, специализирующийся на анализе рентгеновских снимков сетчатки глаза.
Проанализируйте предоставленный снимок сетчатки и предоставьте краткое, но детальное медицинское заключение.

Структура заключения должна включать:
1. Общее описание снимка
2. Выявленные патологии или отклонения
3. Состояние сосудов сетчатки
4. Оценка макулярной области
5. Рекомендации для дальнейшего обследования или лечения

Используйте медицинскую терминологию и будьте максимально точны в описании.""",
    
    "optic_nerve": """Вы - опытный офтальмолог, специализирующийся на анализе зрительного нерва.
Проанализируйте предоставленный снимок зрительного нерва и предоставьте детальное медицинское заключение.

Структура заключения должна включать:
1. Оценка диска зрительного нерва
2. Состояние нейроретинального ободка
3. Соотношение экскавации и диска (C/D ratio)
4. Выявленные патологии (глаукома, атрофия и т.д.)
5. Рекомендации для дальнейшего обследования или лечения

Используйте медицинскую терминологию и будьте максимально точны в описании.""",
    
    "macular_analysis": """Вы - опытный офтальмолог, специализирующийся на анализе макулярной области.
Проанализируйте предоставленный снимок макулярной области и предоставьте детальное медицинское заключение.

Структура заключения должна включать:
1. Состояние фовеальной области
2. Наличие друз или пигментных изменений
3. Признаки макулярной дегенерации
4. Оценка толщины сетчатки в макулярной зоне
5. Рекомендации для дальнейшего обследования или лечения

Используйте медицинскую терминологию и будьте максимально точны в описании.""",
    
    "ultrasound_thyroid": """Вы - опытный врач-диагност, специализирующийся на ультразвуковой диагностике щитовидной железы.
Проанализируйте предоставленное УЗИ-изображение щитовидной железы и предоставьте детальное медицинское заключение.

Структура заключения должна включать:
1. Размеры и объем щитовидной железы
2. Эхогенность и структура паренхимы
3. Наличие узловых образований (размер, локализация, эхогенность)
4. Состояние регионарных лимфоузлов
5. Кровоток (при наличии допплерографии)
6. Выявленные патологии
7. Рекомендации для дальнейшего обследования или лечения

Используйте медицинскую терминологию и будьте максимально точны в описании.""",
    
    "ultrasound_liver": """Вы - опытный врач-диагност, специализирующийся на ультразвуковой диагностике печени.
Проанализируйте предоставленное УЗИ-изображение печени и предоставьте детальное медицинское заключение.

Структура заключения должна включать:
1. Размеры печени
2. Эхогенность и структура паренхимы
3. Контуры печени
4. Наличие очаговых образований (кисты, гемангиомы, опухоли и т.д.)
5. Состояние внутрипеченочных протоков и сосудов
6. Состояние желчного пузыря (если визуализируется)
7. Выявленные патологии
8. Рекомендации для дальнейшего обследования или лечения

Используйте медицинскую терминологию и будьте максимально точны в описании.""",
    
    "lab_blood": """Вы - опытный врач-лаборант и терапевт.
Проанализируйте результаты лабораторных анализов крови и предоставьте детальное медицинское заключение.

Структура заключения:
1. Основные отклонения от референсных значений
2. Возможные причины выявленных отклонений
3. Оценка функции основных систем (печень, почки, кроветворение)
4. Клиническая значимость результатов
5. Рекомендации по дальнейшей диагностике

Используйте медицинскую терминологию и будьте максимально точны в описании.""",

    "brain": """Вы - опытный врач-рентгенолог, специализирующийся на нейровизуализации (МРТ/КТ головного мозга).
Проанализируйте предоставленный снимок головного мозга и предоставьте медицинское заключение.

Структура заключения:
1. Описание структуры вещества головного мозга
2. Состояние желудочковой системы и субарахноидальных пространств
3. Выявленные патологические изменения (очаги, объемные образования и т.д.)
4. Заключение (синдромальный или нозологический диагноз)
5. Рекомендации

Используйте строгую медицинскую терминологию.""",

    "lungs": """Вы - опытный врач-рентгенолог, специализирующийся на диагностике органов грудной клетки (Рентген/КТ).
Проанализируйте предоставленный снимок легких и предоставьте медицинское заключение.

Структура заключения:
1. Состояние легочных полей и легочного рисунка
2. Состояние корней легких, средостения и куполов диафрагмы
3. Выявленные патологии (инфильтрации, образования, плеврит и т.д.)
4. Заключение
5. Рекомендации

Используйте строгую медицинскую терминологию.""",

    "bone": """Вы - опытный врач-рентгенолог, специализирующийся на диагностике опорно-двигательного аппарата (Рентген/КТ/МРТ).
Проанализируйте предоставленный снимок костей и суставов и предоставьте медицинское заключение.

Структура заключения:
1. Состояние костной ткани и суставных щелей
2. Травматические изменения (переломы, вывихи) или дегенеративные изменения
3. Состояние окружающих мягких тканей
4. Заключение
5. Рекомендации

Используйте строгую медицинскую терминологию.""",

    "eye": """Вы - опытный офтальмолог.
Проанализируйте предоставленный снимок органов зрения и предоставьте медицинское заключение.

Структура заключения:
1. Общее описание снимка
2. Выявленные патологии
3. Заключение
4. Рекомендации

Используйте строгую медицинскую терминологию."""
}


async def analyze_xray_image(image_url: str, study_type: StudyType, user_query: Optional[str] = None) -> str:
    """Analyze X-ray image using LLM"""
    # For free_query, use a general medical prompt
    if study_type == "free_query":
        system_prompt = """Вы - опытный врач-диагност, специализирующийся на анализе медицинских изображений.
Проанализируйте предоставленное изображение и ответьте на вопрос пользователя максимально подробно и профессионально.
Используйте медицинскую терминологию и будьте точны в описании."""
    else:
        system_prompt = STUDY_TYPE_PROMPTS[study_type]
    
    print(f"[Analyze] Starting analysis for study_type={study_type}, image_url length={len(image_url) if image_url else 0}, user_query={bool(user_query)}")
    
    try:
        # Prepare user message text
        if user_query:
            user_text = user_query
        else:
            user_text = "Пожалуйста, проанализируйте этот рентгеновский снимок глаза и предоставьте детальное медицинское заключение."
        
        messages: List[Message] = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": user_text,
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_url,
                            "detail": "high",
                        },
                    },
                ],
            },
        ]
        
        print(f"[Analyze] Calling invoke_llm with {len(messages)} messages")
        response = await invoke_llm(messages)
        print(f"[Analyze] Received response from LLM")
        
        analysis_result = response.get("choices", [{}])[0].get("message", {}).get("content")
        
        if not analysis_result or not isinstance(analysis_result, str):
            raise ValueError("No analysis result received from AI")
        
        print(f"[Analyze] Analysis completed, result length={len(analysis_result)}")
        return analysis_result
    except Exception as error:
        print(f"[Analyze] Error analyzing image: {type(error).__name__}: {error}")
        import traceback
        print(f"[Analyze] Traceback: {traceback.format_exc()}")
        raise ValueError(f"Failed to analyze image with AI: {error}")


async def analyze_template_form(image_url: str, template: List[dict]) -> str:
    """Analyze image and fill template form using LLM"""
    print(f"[TemplateForm] Starting analysis, image_url length={len(image_url) if image_url else 0}, template fields={len(template)}")
    
    try:
        # Convert Pydantic models to dicts if needed
        template_dicts = []
        for field in template:
            if hasattr(field, 'dict'):
                # Pydantic model
                template_dicts.append(field.dict())
            elif hasattr(field, '__dict__'):
                # Object with __dict__
                template_dicts.append(field.__dict__)
            else:
                # Already a dict
                template_dicts.append(field)
        
        # Filter only included fields
        included_fields = [f for f in template_dicts if f.get("included", True)]
        
        if not included_fields:
            raise ValueError("No included fields in template")
        
        # Build template structure for prompt
        template_structure = []
        for field in included_fields:
            field_name = field.get("name", "").strip()
            field_value = field.get("value", "").strip()
            if field_name:
                template_structure.append({
                    "name": field_name,
                    "value": field_value if field_value else None,  # None means empty, needs to be filled
                    "filled": bool(field_value)
                })
        
        # Create system prompt
        system_prompt = """Вы - опытный врач-диагност, специализирующийся на анализе медицинских изображений.
Ваша задача - заполнить форму по шаблону на основе анализа предоставленного изображения.

ВАЖНО:
1. Заполненные поля (где указано значение) НЕ изменяйте - оставьте их значения как есть
2. Заполните только пустые поля (где значение null или пустое)
3. Верните результат ТОЛЬКО в формате JSON, без дополнительного текста
4. JSON должен содержать только те поля, которые нужно заполнить (пустые поля)
5. Используйте медицинскую терминологию и будьте точны в описании

Формат ответа: {"название_поля": "заполненное_значение", ...}"""
        
        # Create user prompt with template structure
        template_json = json.dumps(template_structure, ensure_ascii=False, indent=2)
        user_text = f"""Проанализируйте предоставленное медицинское изображение и заполните форму по следующему шаблону:

{template_json}

Заполненные поля (где указано значение) не изменяйте. Заполните только пустые поля (где значение null).
Верните результат в формате JSON с заполненными значениями для пустых полей."""
        
        messages: List[Message] = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": user_text,
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_url,
                            "detail": "high",
                        },
                    },
                ],
            },
        ]
        
        print(f"[TemplateForm] Calling invoke_llm with {len(messages)} messages")
        response = await invoke_llm(messages)
        print(f"[TemplateForm] Received response from LLM")
        
        ai_response = response.get("choices", [{}])[0].get("message", {}).get("content")
        
        if not ai_response or not isinstance(ai_response, str):
            raise ValueError("No response received from AI")
        
        # Parse JSON response
        try:
            # Try to extract JSON from response (in case there's extra text)
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', ai_response, re.DOTALL)
            if json_match:
                filled_fields = json.loads(json_match.group())
            else:
                filled_fields = json.loads(ai_response)
        except json.JSONDecodeError as e:
            print(f"[TemplateForm] Failed to parse JSON: {e}")
            print(f"[TemplateForm] Response was: {ai_response[:500]}")
            raise ValueError(f"Failed to parse AI response as JSON: {e}")
        
        # Merge filled fields with original template
        result_fields = []
        for field in template_structure:
            field_name = field["name"]
            original_value = field["value"]
            
            # If field was already filled, keep original value
            if field["filled"]:
                result_fields.append({
                    "name": field_name,
                    "value": original_value,
                    "filled_by_ai": False
                })
            # If field was empty and AI filled it, use AI value
            elif field_name in filled_fields:
                result_fields.append({
                    "name": field_name,
                    "value": filled_fields[field_name],
                    "filled_by_ai": True
                })
            # If field was empty and AI didn't fill it, leave empty
            else:
                result_fields.append({
                    "name": field_name,
                    "value": "",
                    "filled_by_ai": False
                })
        
        # Format result as structured template (протокол)
        result_lines = []
        result_lines.append("### Протокол сопровождения ОСТ-снимка (макулярная область / задний полюс)\n")
        
        # Group fields by sections (based on field names)
        section_i = []
        section_ii = []
        section_iii = []
        section_iv = []
        other_fields = []
        
        for field in result_fields:
            name = field['name']
            value = field['value'] or '(не заполнено)'
            marker = "✓" if field["filled_by_ai"] else ""
            
            field_line = f"{marker} {name}: {value}"
            
            # Categorize by section based on field names
            if any(keyword in name.lower() for keyword in ['модель', 'режим', 'область сканирования', 'количество срезов', 'усреднение', 'индекс качества', 'артефакт', 'номер центрального', 'толщина сетчатки', 'etdrs', 'сторона глаза', 'фокус', 'контакт линзы', 'технические особенности']):
                section_i.append(field_line)
            elif any(keyword in name.lower() for keyword in ['оптические среды', 'фовеальная', 'субретинальная', 'внутрисетчаточная', 'отслойка', 'слоистость', 'пигментный эпителий', 'гиалоидная', 'структурные особенности']):
                section_ii.append(field_line)
            elif any(keyword in name.lower() for keyword in ['профиль макулы', 'характер жидкости', 'описание жидкости', 'витреомакулярный', 'состояние rpe', 'толщинный паттерн', 'паттерн заболевания']):
                section_iii.append(field_line)
            elif any(keyword in name.lower() for keyword in ['ост-признаки', 'интерпретация', 'заключение', 'динамическое наблюдение', 'сопоставление', 'консультация', 'рекомендации']):
                section_iv.append(field_line)
            else:
                other_fields.append(field_line)
        
        # Format sections
        if section_i:
            result_lines.append("\nI. Техническая часть\n")
            result_lines.extend([f"  {line}" for line in section_i])
        
        if section_ii:
            result_lines.append("\nII. Описание структуры сетчатки (по ОСТ)\n")
            result_lines.extend([f"  {line}" for line in section_ii])
        
        if section_iii:
            result_lines.append("\nIII. Анализ паттернов (оценка по ОСТ)\n")
            result_lines.extend([f"  {line}" for line in section_iii])
        
        if section_iv:
            result_lines.append("\nIV. Заключение\n")
            result_lines.extend([f"  {line}" for line in section_iv])
        
        if other_fields:
            result_lines.append("\nПрочие поля\n")
            result_lines.extend([f"  {line}" for line in other_fields])
        
        result_text = "\n".join(result_lines)
        
        print(f"[TemplateForm] Analysis completed, filled {sum(1 for f in result_fields if f['filled_by_ai'])} fields")
        return result_text
        
    except Exception as error:
        print(f"[TemplateForm] Error analyzing template form: {type(error).__name__}: {error}")
        import traceback
        print(f"[TemplateForm] Traceback: {traceback.format_exc()}")
        raise ValueError(f"Failed to analyze template form with AI: {error}")

