import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';

export default function ThreeBackground({ theme = 'dark' }) {
  const containerRef = useRef(null);
  const themeRef = useRef(theme);

  useEffect(() => {
    themeRef.current = theme;
  }, [theme]);

  useEffect(() => {
    if (!containerRef.current) return;

    // 1. Scene, Camera, Renderer Setup
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(
      55,
      window.innerWidth / window.innerHeight,
      1,
      2500
    );
    camera.position.set(0, 0, 540);

    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(window.innerWidth, window.innerHeight);
    containerRef.current.appendChild(renderer.domElement);

    // 2. Color Palettes for Dark / Light Themes
    const palettes = {
      dark: {
        globeMesh: new THREE.Color(0x6366f1),     // Indigo
        globeInner: new THREE.Color(0x1e1b4b),    // Deep Navy
        ring: new THREE.Color(0x06b6d4),          // Cyan
        accent: new THREE.Color(0xc084fc),        // Purple
        particles: new THREE.Color(0x818cf8),     // Soft Indigo
      },
      light: {
        globeMesh: new THREE.Color(0x3b82f6),     // Blue
        globeInner: new THREE.Color(0xe0e7ff),    // Soft Blue Tint
        ring: new THREE.Color(0x8b5cf6),          // Violet
        accent: new THREE.Color(0xec4899),        // Pink
        particles: new THREE.Color(0x60a5fa),     // Light Blue
      },
    };

    let activePalette = themeRef.current === 'light' ? palettes.light : palettes.dark;

    // 3. Lighting Setup
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.85);
    scene.add(ambientLight);

    const rightLight = new THREE.PointLight(activePalette.globeMesh.getHex(), 4, 1000);
    rightLight.position.set(420, 200, 300);
    scene.add(rightLight);

    const leftLight = new THREE.PointLight(activePalette.ring.getHex(), 4, 1000);
    leftLight.position.set(-420, -200, 300);
    scene.add(leftLight);

    // =========================================================================
    // 4. RIGHT FLANK: CONTINUOUSLY ROTATING & FLOATING 3D GLOBE (X: +420)
    // =========================================================================
    const rightGlobeGroup = new THREE.Group();
    rightGlobeGroup.position.set(420, 15, -20);

    const globeRadius = 210;
    const globeGeo = new THREE.SphereGeometry(globeRadius, 36, 24);
    const globeMat = new THREE.MeshPhongMaterial({
      color: activePalette.globeMesh,
      wireframe: true,
      transparent: true,
      opacity: 0.48,
      shininess: 90,
    });
    const globeMesh = new THREE.Mesh(globeGeo, globeMat);
    rightGlobeGroup.add(globeMesh);

    // Inner Atmosphere Core
    const innerGeo = new THREE.SphereGeometry(globeRadius - 6, 32, 32);
    const innerMat = new THREE.MeshBasicMaterial({
      color: activePalette.globeInner,
      transparent: true,
      opacity: 0.5,
    });
    const innerMesh = new THREE.Mesh(innerGeo, innerMat);
    rightGlobeGroup.add(innerMesh);

    // Orbiting Equatorial Ring
    const ringGeo = new THREE.TorusGeometry(globeRadius + 48, 1.4, 16, 100);
    const ringMat = new THREE.MeshBasicMaterial({
      color: activePalette.ring,
      wireframe: true,
      transparent: true,
      opacity: 0.55,
    });
    const ringMesh = new THREE.Mesh(ringGeo, ringMat);
    ringMesh.rotation.x = Math.PI / 2.6;
    rightGlobeGroup.add(ringMesh);

    // Outer Orbiting Satellite Ring
    const ring2Geo = new THREE.TorusGeometry(globeRadius + 90, 0.9, 12, 80);
    const ring2Mat = new THREE.MeshBasicMaterial({
      color: activePalette.accent,
      wireframe: true,
      transparent: true,
      opacity: 0.4,
    });
    const ring2Mesh = new THREE.Mesh(ring2Geo, ring2Mat);
    ring2Mesh.rotation.y = Math.PI / 3.2;
    rightGlobeGroup.add(ring2Mesh);

    // Surface Data Nodes
    const nodeCount = 120;
    const nodeGeo = new THREE.BufferGeometry();
    const nodePositions = new Float32Array(nodeCount * 3);

    for (let i = 0; i < nodeCount; i++) {
      const phi = Math.acos(-1 + (2 * i) / nodeCount);
      const theta = Math.sqrt(nodeCount * Math.PI) * phi;

      nodePositions[i * 3] = (globeRadius + 2) * Math.cos(theta) * Math.sin(phi);
      nodePositions[i * 3 + 1] = (globeRadius + 2) * Math.sin(theta) * Math.sin(phi);
      nodePositions[i * 3 + 2] = (globeRadius + 2) * Math.cos(phi);
    }

    nodeGeo.setAttribute('position', new THREE.BufferAttribute(nodePositions, 3));
    const nodeMat = new THREE.PointsMaterial({
      color: activePalette.accent,
      size: 5.2,
      transparent: true,
      opacity: 0.95,
    });
    const nodePoints = new THREE.Points(nodeGeo, nodeMat);
    rightGlobeGroup.add(nodePoints);

    scene.add(rightGlobeGroup);

    // =========================================================================
    // 5. LEFT FLANK: CONTINUOUSLY ROTATING & FLOATING CYBER CORE (X: -420)
    // =========================================================================
    const leftGlobeGroup = new THREE.Group();
    leftGlobeGroup.position.set(-420, -15, -20);

    const leftRadius = 185;
    const leftGlobeGeo = new THREE.IcosahedronGeometry(leftRadius, 2);
    const leftGlobeMat = new THREE.MeshPhongMaterial({
      color: activePalette.ring,
      wireframe: true,
      transparent: true,
      opacity: 0.45,
      shininess: 85,
    });
    const leftGlobeMesh = new THREE.Mesh(leftGlobeGeo, leftGlobeMat);
    leftGlobeGroup.add(leftGlobeMesh);

    // Left Inner Reactor Octahedron
    const leftInnerGeo = new THREE.OctahedronGeometry(leftRadius - 60, 1);
    const leftInnerMat = new THREE.MeshStandardMaterial({
      color: activePalette.accent,
      wireframe: true,
      transparent: true,
      opacity: 0.75,
    });
    const leftInnerMesh = new THREE.Mesh(leftInnerGeo, leftInnerMat);
    leftGlobeGroup.add(leftInnerMesh);

    // Left Torus Ring
    const leftRingGeo = new THREE.TorusGeometry(leftRadius + 46, 1.2, 16, 90);
    const leftRingMat = new THREE.MeshBasicMaterial({
      color: activePalette.globeMesh,
      wireframe: true,
      transparent: true,
      opacity: 0.5,
    });
    const leftRingMesh = new THREE.Mesh(leftRingGeo, leftRingMat);
    leftRingMesh.rotation.x = -Math.PI / 3;
    leftGlobeGroup.add(leftRingMesh);

    scene.add(leftGlobeGroup);

    // =========================================================================
    // 6. AMBIENT BACKGROUND PARTICLE DRIFT STREAM
    // =========================================================================
    const particleCount = 240;
    const particleGeo = new THREE.BufferGeometry();
    const pPositions = new Float32Array(particleCount * 3);
    const pVelocities = [];

    for (let i = 0; i < particleCount; i++) {
      const x = (Math.random() - 0.5) * 1350;
      const y = (Math.random() - 0.5) * 950;
      const z = (Math.random() - 0.5) * 450;

      pPositions[i * 3] = x;
      pPositions[i * 3 + 1] = y;
      pPositions[i * 3 + 2] = z;

      pVelocities.push({
        x: (Math.random() - 0.5) * 0.6,
        y: (Math.random() - 0.5) * 0.6,
        z: (Math.random() - 0.5) * 0.3,
      });
    }

    particleGeo.setAttribute('position', new THREE.BufferAttribute(pPositions, 3));
    const particleMat = new THREE.PointsMaterial({
      color: activePalette.particles,
      size: 4.2,
      transparent: true,
      opacity: 0.65,
    });
    const particleSystem = new THREE.Points(particleGeo, particleMat);
    scene.add(particleSystem);

    // =========================================================================
    // 7. CONTINUOUS HIGH-VELOCITY ANIMATION ENGINE
    // =========================================================================
    let mouseX = 0;
    let mouseY = 0;

    const handleMouseMove = (e) => {
      mouseX = (e.clientX - window.innerWidth / 2) * 0.2;
      mouseY = (e.clientY - window.innerHeight / 2) * 0.2;
    };

    window.addEventListener('mousemove', handleMouseMove);

    const handleResize = () => {
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
    };

    window.addEventListener('resize', handleResize);

    let animationFrameId;
    let time = 0;

    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);
      time += 0.02;

      // Theme Color Interpolation
      const targetPalette = themeRef.current === 'light' ? palettes.light : palettes.dark;
      globeMat.color.lerp(targetPalette.globeMesh, 0.05);
      innerMat.color.lerp(targetPalette.globeInner, 0.05);
      ringMat.color.lerp(targetPalette.ring, 0.05);
      ring2Mat.color.lerp(targetPalette.accent, 0.05);
      nodeMat.color.lerp(targetPalette.accent, 0.05);
      leftGlobeMat.color.lerp(targetPalette.ring, 0.05);
      leftInnerMat.color.lerp(targetPalette.accent, 0.05);
      leftRingMat.color.lerp(targetPalette.globeMesh, 0.05);
      particleMat.color.lerp(targetPalette.particles, 0.05);
      rightLight.color.lerp(targetPalette.globeMesh, 0.05);
      leftLight.color.lerp(targetPalette.ring, 0.05);

      // A. Dynamic Floating Orbit Drift across Canvas
      rightGlobeGroup.position.x = 420 + Math.sin(time * 0.9) * 55;
      rightGlobeGroup.position.y = 15 + Math.cos(time * 0.8) * 35;
      rightGlobeGroup.position.z = -20 + Math.sin(time * 0.5) * 25;

      leftGlobeGroup.position.x = -420 - Math.sin(time * 0.9) * 55;
      leftGlobeGroup.position.y = -15 - Math.cos(time * 0.8) * 35;
      leftGlobeGroup.position.z = -20 + Math.cos(time * 0.5) * 25;

      // B. ENTIRE 3D GROUP ROTATION (Spinning whole globe assemblies!)
      // Add interaction speed based on mouse movement distance from center
      const interactionSpeed = 1 + (Math.abs(mouseX) + Math.abs(mouseY)) * 0.02;
      
      rightGlobeGroup.rotation.y += 0.015 * interactionSpeed;
      rightGlobeGroup.rotation.x += 0.010 * interactionSpeed;

      leftGlobeGroup.rotation.y -= 0.018 * interactionSpeed;
      leftGlobeGroup.rotation.z += 0.012 * interactionSpeed;

      // C. Sub-mesh internal counter-rotations
      globeMesh.rotation.y += 0.012 * interactionSpeed;
      ringMesh.rotation.z += 0.020 * interactionSpeed;
      ring2Mesh.rotation.z -= 0.018 * interactionSpeed;

      leftGlobeMesh.rotation.y -= 0.015 * interactionSpeed;
      leftInnerMesh.rotation.y += 0.020 * interactionSpeed;
      leftRingMesh.rotation.z += 0.022 * interactionSpeed;

      // D. Particle Stream Drifting
      const pArr = particleGeo.attributes.position.array;
      for (let i = 0; i < particleCount; i++) {
        pArr[i * 3] += pVelocities[i].x;
        pArr[i * 3 + 1] += pVelocities[i].y;
        pArr[i * 3 + 2] += pVelocities[i].z;

        if (Math.abs(pArr[i * 3]) > 700) pVelocities[i].x *= -1;
        if (Math.abs(pArr[i * 3 + 1]) > 500) pVelocities[i].y *= -1;
        if (Math.abs(pArr[i * 3 + 2]) > 280) pVelocities[i].z *= -1;
      }
      particleGeo.attributes.position.needsUpdate = true;

      // E. Smooth Camera Parallax Response
      camera.position.x += (mouseX - camera.position.x) * 0.04;
      camera.position.y += (-mouseY - camera.position.y) * 0.04;
      camera.lookAt(scene.position);

      renderer.render(scene, camera);
    };

    animate();

    const container = containerRef.current;

    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('resize', handleResize);
      renderer.dispose();
      if (container) {
        container.innerHTML = '';
      }
    };
  }, []);

  return (
    <div
      ref={containerRef}
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100vw',
        height: '100vh',
        pointerEvents: 'none',
        zIndex: 0,
        overflow: 'hidden',
      }}
    />
  );
}
