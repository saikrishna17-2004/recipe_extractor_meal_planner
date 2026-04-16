const api = {
  async extract(url) {
    const response = await fetch('/api/extract', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url }),
    });
    return handleJson(response);
  },
  async history() {
    const response = await fetch('/api/recipes');
    return handleJson(response);
  },
  async details(id) {
    const response = await fetch(`/api/recipes/${id}`);
    return handleJson(response);
  },
  async mealPlan(recipeIds) {
    const response = await fetch('/api/meal-plan', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ recipe_ids: recipeIds }),
    });
    return handleJson(response);
  },
};

const state = {
  recipes: [],
  selected: new Set(),
};

const els = {
  tabs: Array.from(document.querySelectorAll('.tab')),
  panels: Array.from(document.querySelectorAll('.panel')),
  recipeUrl: document.getElementById('recipeUrl'),
  extractButton: document.getElementById('extractButton'),
  statusMessage: document.getElementById('statusMessage'),
  recipeResult: document.getElementById('recipeResult'),
  historyTable: document.getElementById('historyTable'),
  refreshHistory: document.getElementById('refreshHistory'),
  recipeCount: document.getElementById('recipeCount'),
  modalBackdrop: document.getElementById('modalBackdrop'),
  modalContent: document.getElementById('modalContent'),
  closeModal: document.getElementById('closeModal'),
  mealPlannerList: document.getElementById('mealPlannerList'),
  buildMealPlan: document.getElementById('buildMealPlan'),
  mealPlanOutput: document.getElementById('mealPlanOutput'),
};

els.tabs.forEach((tab) => {
  tab.addEventListener('click', () => {
    const target = tab.dataset.tab;
    els.tabs.forEach((item) => item.classList.toggle('active', item === tab));
    els.panels.forEach((panel) => panel.classList.toggle('active', panel.id === target));
  });
});

els.extractButton.addEventListener('click', async () => {
  const url = els.recipeUrl.value.trim();
  if (!url) {
    setStatus('Please enter a recipe URL.');
    return;
  }
  setStatus('Extracting recipe...');
  try {
    const recipe = await api.extract(url);
    renderRecipe(recipe, els.recipeResult);
    await refreshHistoryView();
    setStatus(`Saved ${recipe.title}`);
  } catch (error) {
    setStatus(getErrorMessage(error));
  }
});

els.refreshHistory.addEventListener('click', refreshHistoryView);
els.closeModal.addEventListener('click', closeModal);
els.modalBackdrop.addEventListener('click', (event) => {
  if (event.target === els.modalBackdrop) closeModal();
});
els.historyTable.addEventListener('click', async (event) => {
  const button = event.target.closest('[data-details]');
  if (!button) return;
  const recipeId = button.dataset.details;
  if (!recipeId) return;
  await openRecipeDetails(recipeId);
});
els.buildMealPlan.addEventListener('click', async () => {
  const recipeIds = Array.from(state.selected);
  if (!recipeIds.length) {
    els.mealPlanOutput.innerHTML = '<p>Select at least one recipe.</p>';
    return;
  }
  try {
    const result = await api.mealPlan(recipeIds);
    renderMealPlan(result);
  } catch (error) {
    els.mealPlanOutput.innerHTML = `<p>${escapeHtml(getErrorMessage(error))}</p>`;
  }
});

async function refreshHistoryView() {
  try {
    const recipes = await api.history();
    state.recipes = recipes;
    els.recipeCount.textContent = String(recipes.length);
    renderHistory(recipes);
    renderPlanner(recipes);
  } catch (error) {
    state.recipes = [];
    els.recipeCount.textContent = '0';
    els.historyTable.innerHTML = `
      <tr>
        <td colspan="5">Could not load saved recipes: ${escapeHtml(getErrorMessage(error))}</td>
      </tr>
    `;
    els.mealPlannerList.innerHTML = '<p>Meal planner unavailable until recipes load.</p>';
  }
}

function renderRecipe(recipe, container) {
  container.innerHTML = `
    ${cardHtml('Overview', `
      <div class="meta">
        ${field('Title', recipe.title)}
        ${field('Cuisine', recipe.cuisine || 'Unknown')}
        ${field('Prep Time', recipe.prep_time || 'Unknown')}
        ${field('Cook Time', recipe.cook_time || 'Unknown')}
        ${field('Total Time', recipe.total_time || 'Unknown')}
        ${field('Servings', recipe.servings ?? 'Unknown')}
        ${field('Difficulty', recipe.difficulty || 'Unknown')}
      </div>
    `)}
    ${cardHtml('Ingredients', `<ul>${(recipe.ingredients || []).map(formatIngredient).join('')}</ul>`)}
    ${cardHtml('Instructions', `<ol>${(recipe.instructions || []).map((step) => `<li>${escapeHtml(step)}</li>`).join('')}</ol>`)}
    ${cardHtml('Nutrition Estimate', `<div class="details-grid">${nutritionFields(recipe.nutrition_estimate || {})}</div>`)}
    ${cardHtml('Substitutions', `<ul>${(recipe.substitutions || []).map((item) => `<li>${escapeHtml(item)}</li>`).join('')}</ul>`)}
    ${cardHtml('Shopping List', `<div class="details-grid">${shoppingBlocks(recipe.shopping_list || {})}</div>`)}
    ${cardHtml('Related Recipes', `<ul>${(recipe.related_recipes || []).map((item) => `<li>${escapeHtml(item)}</li>`).join('')}</ul>`)}
  `;
}

function renderHistory(recipes) {
  if (!recipes.length) {
    els.historyTable.innerHTML = `
      <tr>
        <td colspan="5">No saved recipes yet. Extract a recipe in the first tab to populate history.</td>
      </tr>
    `;
    return;
  }

  els.historyTable.innerHTML = recipes.map((recipe) => `
    <tr>
      <td>${escapeHtml(recipe.title)}</td>
      <td>${escapeHtml(recipe.cuisine || '')}</td>
      <td>${escapeHtml(recipe.difficulty || '')}</td>
      <td>${formatDate(recipe.created_at)}</td>
      <td><button class="secondary" data-details="${recipe.id}">Details</button></td>
    </tr>
  `).join('');
}

async function openRecipeDetails(recipeId) {
  els.modalContent.innerHTML = '<p>Loading recipe details...</p>';
  els.modalBackdrop.classList.remove('hidden');
  try {
    const recipe = await api.details(recipeId);
    showModal(recipe);
  } catch (error) {
    els.modalContent.innerHTML = `<p>${escapeHtml(getErrorMessage(error))}</p>`;
  }
}

function renderPlanner(recipes) {
  if (!recipes.length) {
    els.mealPlannerList.innerHTML = '<p>No recipes available for meal planning yet.</p>';
    return;
  }

  els.mealPlannerList.innerHTML = recipes.map((recipe) => `
    <label class="planner-item">
      <input type="checkbox" data-plan-id="${recipe.id}" ${state.selected.has(recipe.id) ? 'checked' : ''} />
      <span>
        <strong>${escapeHtml(recipe.title)}</strong><br />
        <small>${escapeHtml(recipe.cuisine || 'Unknown')} · ${escapeHtml(recipe.difficulty || 'Unknown')}</small>
      </span>
    </label>
  `).join('');

  els.mealPlannerList.querySelectorAll('[data-plan-id]').forEach((checkbox) => {
    checkbox.addEventListener('change', () => {
      const id = Number(checkbox.dataset.planId);
      if (checkbox.checked) {
        state.selected.add(id);
      } else {
        state.selected.delete(id);
      }
    });
  });
}

function showModal(recipe) {
  els.modalContent.innerHTML = `
    <h2>${escapeHtml(recipe.title)}</h2>
    <p>${escapeHtml(recipe.url)}</p>
    ${cardHtml('Recipe Details', `
      <div class="details-grid">
        ${field('Cuisine', recipe.cuisine || 'Unknown')}
        ${field('Prep Time', recipe.prep_time || 'Unknown')}
        ${field('Cook Time', recipe.cook_time || 'Unknown')}
        ${field('Total Time', recipe.total_time || 'Unknown')}
        ${field('Servings', recipe.servings ?? 'Unknown')}
        ${field('Difficulty', recipe.difficulty || 'Unknown')}
      </div>
    `)}
    ${cardHtml('Ingredients', `<ul>${(recipe.ingredients || []).map(formatIngredient).join('')}</ul>`)}
    ${cardHtml('Instructions', `<ol>${(recipe.instructions || []).map((step) => `<li>${escapeHtml(step)}</li>`).join('')}</ol>`)}
    ${cardHtml('Nutrition Estimate', `<div class="details-grid">${nutritionFields(recipe.nutrition_estimate || {})}</div>`)}
    ${cardHtml('Substitutions', `<ul>${(recipe.substitutions || []).map((item) => `<li>${escapeHtml(item)}</li>`).join('')}</ul>`)}
    ${cardHtml('Shopping List', `<div class="details-grid">${shoppingBlocks(recipe.shopping_list || {})}</div>`)}
    ${cardHtml('Related Recipes', `<ul>${(recipe.related_recipes || []).map((item) => `<li>${escapeHtml(item)}</li>`).join('')}</ul>`)}
  `;
  els.modalBackdrop.classList.remove('hidden');
}

function closeModal() {
  els.modalBackdrop.classList.add('hidden');
}

function renderMealPlan(plan) {
  els.mealPlanOutput.innerHTML = `
    <div class="category-block">
      <h4>Merged Shopping List</h4>
      <div class="details-grid">${shoppingBlocks(plan.shopping_list || {})}</div>
    </div>
  `;
}

function cardHtml(title, content) {
  return `<section class="card"><h3>${escapeHtml(title)}</h3>${content}</section>`;
}

function field(label, value) {
  return `<div class="kv"><small>${escapeHtml(label)}</small>${escapeHtml(String(value))}</div>`;
}

function nutritionFields(nutrition) {
  return Object.entries(nutrition).map(([key, value]) => field(key, value)).join('');
}

function shoppingBlocks(shoppingList) {
  return Object.entries(shoppingList).map(([category, items]) => `
    <div class="category-block">
      <h4>${escapeHtml(category)}</h4>
      <ul>${items.map((item) => `<li>${escapeHtml(item)}</li>`).join('')}</ul>
    </div>
  `).join('');
}

function formatIngredient(item) {
  const pieces = [item.quantity, item.unit, item.item].filter(Boolean).join(' ');
  return `<li>${escapeHtml(pieces)}</li>`;
}

function setStatus(message) {
  els.statusMessage.textContent = message;
}

function formatDate(value) {
  if (!value) return '';
  return new Date(value).toLocaleString();
}

function getErrorMessage(error) {
  return error?.message || 'Something went wrong.';
}

async function handleJson(response) {
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.detail || payload.message || 'Request failed');
  }
  return payload;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

refreshHistoryView().catch((error) => setStatus(getErrorMessage(error)));
