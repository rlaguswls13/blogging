/**
 * TECH LOG - Category Tags 12-Limit & Dynamic Modal Engine
 */
(function() {
  'use strict';

  function ensureCategoriesModalExists() {
    if (document.getElementById('categories-modal')) return;

    var modalDiv = document.createElement('div');
    modalDiv.id = 'categories-modal';
    modalDiv.className = 'modal-overlay';
    modalDiv.style.display = 'none';
    modalDiv.innerHTML = 
      '<div class="modal-box">' +
        '<div class="modal-header">' +
          '<h3>전체 카테고리</h3>' +
          '<button class="modal-close-btn" id="modal-close-btn-x">×</button>' +
        '</div>' +
        '<div class="modal-body">' +
          '<div class="devlog-tags-popup" id="modal-tags-container"></div>' +
        '</div>' +
      '</div>';
    
    document.body.appendChild(modalDiv);

    var closeBtn = document.getElementById('modal-close-btn-x');
    if (closeBtn) {
      closeBtn.addEventListener('click', closeCategoriesModal);
    }
  }

  function initCategoryTagsLimit() {
    ensureCategoriesModalExists();

    var widget = document.getElementById('Label1') || document.querySelector('.widget.Label') || document.querySelector('[id^="Label"]');
    if (!widget) return;

    var container = widget.querySelector('.widget-content') || widget;
    if (!container || container.querySelector('.devlog-tags')) return;

    var anchors = Array.from(container.querySelectorAll('a'));
    if (anchors.length === 0) return;

    var tagsData = [];
    anchors.forEach(function(a) {
      var rawText = a.textContent.trim();
      if (!rawText) return;

      var name = rawText;
      var count = "";
      
      var match = rawText.match(/(.+?)\s*\((\d+)\)$/);
      if (match) {
        name = match[1].trim();
        count = match[2];
      } else {
        var countSpan = a.querySelector('.label-count, .count') || (a.nextElementSibling && a.nextElementSibling.className && a.nextElementSibling.className.indexOf('count') !== -1 ? a.nextElementSibling : null);
        if (countSpan) {
          count = countSpan.textContent.replace(/[()]/g, '').trim();
          name = rawText.replace(countSpan.textContent, '').trim();
        }
      }

      tagsData.push({
        name: name,
        count: count,
        url: a.getAttribute('href')
      });
    });

    if (tagsData.length === 0) return;

    // 카테고리 정렬: 글 수 내림차순 -> 이름 오름차순
    tagsData.sort(function(a, b) {
      var countA = a.count ? parseInt(a.count, 10) : 0;
      var countB = b.count ? parseInt(b.count, 10) : 0;
      if (countA !== countB) return countB - countA;
      return a.name.localeCompare(b.name, 'ko', { sensitivity: 'base' });
    });

    // 기존 내용 비우고 모던 devlog-tags 칩 박스로 렌더링
    container.innerHTML = '';
    var tagsBox = document.createElement('div');
    tagsBox.className = 'devlog-tags';
    container.appendChild(tagsBox);

    // 상위 12개 렌더링
    tagsData.forEach(function(tag, idx) {
      if (idx < 12) {
        var tagEl = document.createElement('a');
        tagEl.href = tag.url;
        tagEl.className = 'tech-tag';
        tagEl.textContent = tag.name;
        if (tag.count) {
          var cEl = document.createElement('span');
          cEl.className = 'label-count';
          cEl.style.marginLeft = '4px';
          cEl.style.fontWeight = '700';
          cEl.style.color = 'var(--primary-color, #2563eb)';
          cEl.textContent = '(' + tag.count + ')';
          tagEl.appendChild(cEl);
        }
        tagsBox.appendChild(tagEl);
      }
    });

    // 12개 초과 시 '...' 모달 더보기 버튼 렌더링 (13번째 위치)
    if (tagsData.length > 12) {
      var moreBtn = document.createElement('button');
      moreBtn.className = 'tech-tag-more-btn';
      moreBtn.textContent = '...';
      moreBtn.style.color = 'var(--primary-color, #2563eb)';
      moreBtn.style.fontWeight = '700';
      moreBtn.style.padding = '0.35rem 0.75rem';
      moreBtn.style.background = 'var(--card-bg, #ffffff)';
      moreBtn.style.border = '1px solid var(--border-color, #e2e8f0)';
      moreBtn.style.borderRadius = '20px';
      moreBtn.style.cursor = 'pointer';
      moreBtn.style.display = 'inline-flex';
      moreBtn.style.alignItems = 'center';
      moreBtn.style.justifyContent = 'center';
      moreBtn.style.transition = 'all 0.2s';
      
      moreBtn.addEventListener('click', function(e) {
        e.preventDefault();
        showAllCategoriesModal(tagsData);
      });
      tagsBox.appendChild(moreBtn);
    }
  }

  function showAllCategoriesModal(tagsData) {
    ensureCategoriesModalExists();
    var modal = document.getElementById('categories-modal');
    var modalContainer = document.getElementById('modal-tags-container');
    if (!modal || !modalContainer) return;

    modalContainer.innerHTML = '';
    var tags = tagsData || [];

    tags.forEach(function(tag) {
      var tagEl = document.createElement('a');
      tagEl.href = tag.url;
      tagEl.className = 'tech-tag';
      tagEl.textContent = tag.name;
      tagEl.style.display = 'inline-flex';
      if (tag.count) {
        var countEl = document.createElement('span');
        countEl.className = 'label-count';
        countEl.style.marginLeft = '4px';
        countEl.style.fontWeight = '700';
        countEl.style.color = 'var(--primary-color, #2563eb)';
        countEl.textContent = '(' + tag.count + ')';
        tagEl.appendChild(countEl);
      }
      modalContainer.appendChild(tagEl);
    });

    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden';
  }

  function closeCategoriesModal() {
    var modal = document.getElementById('categories-modal');
    if (modal) {
      modal.style.display = 'none';
      document.body.style.overflow = '';
    }
  }

  document.addEventListener("DOMContentLoaded", function() {
    ensureCategoriesModalExists();
    initCategoryTagsLimit();
    setTimeout(initCategoryTagsLimit, 300);
    setTimeout(initCategoryTagsLimit, 1000);
  });

  window.addEventListener('click', function(e) {
    var modal = document.getElementById('categories-modal');
    if (e.target === modal) {
      closeCategoriesModal();
    }
  });

})();
