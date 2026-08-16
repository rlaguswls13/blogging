/**
 * TECH LOG - Unified Blogger Theme Frontend Engine
 * Handles Dynamic AJAX Card Paging, Category Tags 12-Limit & Modal Popup, and Mermaid Diagram Rendering.
 */
(function() {
  'use strict';

  // =========================================================
  // 1. 카테고리 칩 12개 제한 및 ... 더보기 팝업 모달 Engine
  // =========================================================
  function initCategoryTagsLimit() {
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

    // 글 수 내림차순 -> 이름 오름차순 정렬
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
    var modal = document.getElementById('categories-modal');
    var modalContainer = document.getElementById('modal-tags-container');
    if (!modal || !modalContainer) return;

    modalContainer.innerHTML = '';
    var tags = tagsData || [];

    if (tags.length === 0) {
      var sourceTags = document.querySelectorAll('#Label1 .devlog-tags .tech-tag');
      sourceTags.forEach(function(tag) {
        var clone = tag.cloneNode(true);
        clone.style.display = 'inline-flex';
        modalContainer.appendChild(clone);
      });
    } else {
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
    }
    
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

  // =========================================================
  // 2. Blogger Dynamic AJAX Card Pager Engine
  // =========================================================
  var postPerPage = 4;
  var allPosts = [];
  var currentPage = 1;

  function formatBloggerDate(dateStr) {
    if (!dateStr) return '';
    try {
      var d = new Date(dateStr);
      return (d.getMonth() + 1) + '월 ' + d.getDate() + ', ' + d.getFullYear();
    } catch(e) {
      return dateStr;
    }
  }

  function renderPage(page) {
    var container = document.querySelector('#main-posts-grid, .posts-grid, .blog-posts');
    if (!container) return;

    var existingCards = Array.from(container.children);
    if (allPosts.length === 0 && existingCards.length > 0) return;

    currentPage = page;
    var startIdx = (page - 1) * postPerPage;
    var endIdx = startIdx + postPerPage;
    var pagePosts = allPosts.slice(startIdx, endIdx);

    container.innerHTML = '';
    pagePosts.forEach(function(post) {
      var article = document.createElement('article');
      article.className = 'post-card';
      
      var badgeCat = (post.labels && post.labels.length > 0) ? post.labels[0] : 'TECH';
      var tagsHtml = '';
      if (post.labels && post.labels.length > 0) {
        tagsHtml = '<div class="post-tags">';
        post.labels.slice(0, 4).forEach(function(lbl) {
          tagsHtml += '<span class="tech-tag">' + lbl + '</span>';
        });
        tagsHtml += '</div>';
      }

      var formattedDate = formatBloggerDate(post.published);

      article.innerHTML = 
        '<div class="post-card-body">' +
          '<div class="post-category-badge">' + badgeCat + '</div>' +
          '<h2 class="post-card-title"><a href="' + post.url + '">' + post.title + '</a></h2>' +
          tagsHtml +
          '<div class="post-card-meta">' +
            '<span>📅 ' + formattedDate + '</span>' +
          '</div>' +
        '</div>';
      
      container.appendChild(article);
    });

    renderPagerControls();

    // 상단으로 부드러운 스크롤 이동
    window.scrollTo({
      top: container.offsetTop - 100,
      behavior: 'smooth'
    });
  }

  function renderPagerControls() {
    var pager = document.getElementById('blog-pager');
    if (!pager) return;

    var totalPages = Math.ceil(allPosts.length / postPerPage);
    if (totalPages <= 1) {
      pager.style.display = 'none';
      return;
    }

    pager.style.display = 'flex';
    var html = '';

    if (currentPage > 1) {
      html += '<a class="blog-pager-newer-link" href="#" id="prev-page-btn">← 최근 게시물</a>';
    }

    html += '<a class="home-link" href="/">홈 (' + currentPage + '/' + totalPages + ')</a>';

    if (currentPage < totalPages) {
      html += '<a class="blog-pager-older-link" href="#" id="next-page-btn">이전 게시물 →</a>';
    }

    pager.innerHTML = html;

    var prevBtn = document.getElementById('prev-page-btn');
    if (prevBtn) {
      prevBtn.addEventListener('click', function(e) {
        e.preventDefault();
        if (currentPage > 1) renderPage(currentPage - 1);
      });
    }

    var nextBtn = document.getElementById('next-page-btn');
    if (nextBtn) {
      nextBtn.addEventListener('click', function(e) {
        e.preventDefault();
        if (currentPage < totalPages) renderPage(currentPage + 1);
      });
    }
  }

  window.initBloggerFeedPagination = function(json) {
    var entries = (json.feed && json.feed.entry) ? json.feed.entry : [];
    allPosts = [];

    entries.forEach(function(entry) {
      var title = entry.title ? entry.title.$t : '';
      var published = entry.published ? entry.published.$t : '';
      var url = '';
      if (entry.link) {
        for (var i = 0; i < entry.link.length; i++) {
          if (entry.link[i].rel === 'alternate') {
            url = entry.link[i].href;
            break;
          }
        }
      }
      var labels = [];
      if (entry.category) {
        entry.category.forEach(function(cat) {
          if (cat.term) labels.push(cat.term);
        });
      }

      allPosts.push({
        title: title,
        published: published,
        url: url,
        labels: labels
      });
    });

    if (allPosts.length > 0) {
      renderPage(1);
    }
  };

  // =========================================================
  // 3. Event Listeners and Initialization
  // =========================================================
  document.addEventListener("DOMContentLoaded", function() {
    initCategoryTagsLimit();
    setTimeout(initCategoryTagsLimit, 300);
    setTimeout(initCategoryTagsLimit, 1000);

    // 상세 글 페이지가 아닌 경우 동적 AJAX 카드 페이징 갱신
    if (window.location.pathname.indexOf('/20') !== 0 || window.location.pathname.indexOf('.html') === -1) {
      var script = document.createElement('script');
      script.src = '/feeds/posts/summary?alt=json-in-script&max-results=150&callback=initBloggerFeedPagination';
      document.body.appendChild(script);
    }

    // Mermaid Diagram Render
    var mermaidEls = document.querySelectorAll('.mermaid');
    if (mermaidEls.length > 0 && typeof mermaid !== 'undefined') {
      mermaid.initialize({
        startOnLoad: true,
        theme: 'neutral',
        securityLevel: 'loose',
        flowchart: { useMaxWidth: true, htmlLabels: true }
      });
    }
  });

  window.addEventListener('click', function(e) {
    var modal = document.getElementById('categories-modal');
    if (e.target === modal) {
      closeCategoriesModal();
    }
  });

})();
