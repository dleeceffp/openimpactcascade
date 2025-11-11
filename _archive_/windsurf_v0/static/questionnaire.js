document.addEventListener('DOMContentLoaded', () => {
    const container = document.getElementById('questionnaire-container');
    const form = document.getElementById('analysis-form');
    const submitBtn = document.getElementById('submit-btn');
    const questionsData = JSON.parse(document.getElementById('questions-data').textContent);

    function renderQuestion(questionId) {
        container.innerHTML = '';

        if (!questionId) {
            submitBtn.style.display = 'block';
            container.innerHTML = '<p>All questions have been answered. Click \"Analyze Risk\" to see the results.</p>';
            return;
        }

        const question = questionsData.questions[questionId];
        const questionDiv = document.createElement('div');
        questionDiv.className = 'question';

        const questionText = document.createElement('p');
        questionText.className = 'question-text';
        questionText.textContent = question.text;
        questionDiv.appendChild(questionText);

        if (question.type === 'pert_estimate') {
            renderPertEstimate(question, questionDiv);
        } else if (question.type === 'multiple_choice') {
            renderMultipleChoice(question, questionDiv);
        }

        container.appendChild(questionDiv);
    }

    function renderPertEstimate(question, parentDiv) {
        const prompt = document.createElement('p');
        prompt.className = 'prompt';
        prompt.textContent = question.prompt;
        parentDiv.appendChild(prompt);

        ['min', 'mle', 'max'].forEach((field, i) => {
            const label = ['Minimum', 'Most Likely', 'Maximum'][i];
            const inputGroup = document.createElement('div');
            inputGroup.className = 'input-group';
            const labelEl = document.createElement('label');
            labelEl.textContent = `${label}:`;
            const input = document.createElement('input');
            input.type = 'number';
            input.name = question.outputs[field];
            input.step = 'any';
            input.required = true;
            inputGroup.appendChild(labelEl);
            inputGroup.appendChild(input);
            parentDiv.appendChild(inputGroup);
        });

        const nextBtn = document.createElement('button');
        nextBtn.textContent = 'Next';
        nextBtn.type = 'button';
        nextBtn.className = 'next-btn';
        nextBtn.addEventListener('click', () => {
            if (form.checkValidity()) {
                // Persist the data from the current inputs into hidden fields
                const inputs = parentDiv.querySelectorAll('input[type="number"]');
                inputs.forEach(input => {
                    const hiddenInput = document.createElement('input');
                    hiddenInput.type = 'hidden';
                    hiddenInput.name = input.name;
                    hiddenInput.value = input.value;
                    form.appendChild(hiddenInput);
                });

                renderQuestion(question.next_question_id);
            } else {
                alert('Please fill in all required fields.');
            }
        });
        parentDiv.appendChild(nextBtn);
    }

    function renderMultipleChoice(question, parentDiv) {
        question.choices.forEach(choice => {
            const choiceDiv = document.createElement('div');
            choiceDiv.className = 'choice';
            const radio = document.createElement('input');
            radio.type = 'radio';
            radio.name = 'choice';
            radio.value = choice.next_question_id;
            radio.id = choice.next_question_id;
            radio.addEventListener('change', () => {
                renderQuestion(radio.value);
            });
            const label = document.createElement('label');
            label.textContent = choice.text;
            label.htmlFor = choice.next_question_id;
            choiceDiv.appendChild(radio);
            choiceDiv.appendChild(label);
            parentDiv.appendChild(choiceDiv);
        });
    }

    renderQuestion(questionsData.start_question_id);
});
